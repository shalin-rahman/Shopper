from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

import asyncpg
from fastapi import APIRouter, HTTPException, Query, Request

from core.config import Settings
from core.dependencies import SettingsDep, StaffDep
from schemas import PaymentCreate, PaymentGateway, PaymentOut
from core.tenant_context import TenantCtxDep, resolve_tenant_id, tenant_transaction
from services.payment_gateway import get_gateway, get_tenant_settings, payment_row_to_out
from services.payment_settlement import reserve_invoice_payment

router = APIRouter(prefix="/v1/tenant/payments", tags=["payments"])

def _pool(request: Request) -> asyncpg.Pool:
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount if amount.is_finite() else None


async def _ipn_payload_dict(request: Request) -> dict[str, Any]:
    ct = (request.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="IPN JSON must be an object")
        return {str(k): body[k] for k in body}
    form = await request.form()
    return {str(k): str(v) for k, v in form.multi_items()}


def _ipn_refs(gateway: PaymentGateway, data: dict[str, Any]) -> tuple[str, str]:
    """Return (order_reference, gateway_transaction_id) best-effort per gateway."""
    if gateway == PaymentGateway.sslcommerz:
        return str(data.get("tran_id") or "").strip(), str(data.get("val_id") or "").strip()
    return (
        str(
            data.get("order_id")
            or data.get("orderId")
            or data.get("merchantInvoiceNumber")
            or ""
        ).strip(),
        str(
            data.get("transaction_id")
            or data.get("paymentID")
            or data.get("payment_ref_id")
            or data.get("paymentReferenceId")
            or data.get("val_id")
            or ""
        ).strip(),
    )


@router.post("", response_model=PaymentOut, status_code=201)
async def create_payment(ctx: TenantCtxDep, body: PaymentCreate, settings: SettingsDep, _auth: StaffDep):
    tenant_settings = await get_tenant_settings(ctx.request, ctx.tenant_id)
    gateway = get_gateway(body.gateway, settings)
    order_id = body.order_id or str(uuid4())
    gateway_body = body.model_copy(update={"order_id": order_id})

    # Use gateway_transaction_id if returned (bKash returns paymentID here)
    async with ctx.transaction() as conn:
        if body.invoice_id:
            await reserve_invoice_payment(
                conn,
                body.invoice_id,
                body.amount,
                body.currency,
            )

        init_data = await gateway.initiate_payment(
            gateway_body,
            ctx.subdomain,
            settings,
            tenant_settings,
        )
        gw_txn_id = init_data.get("paymentID") or init_data.get("gateway_transaction_id")
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.payments (
                tenant_id, gateway, amount, currency, status, description, order_id,
                gateway_transaction_id, invoice_id
            ) VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8)
            RETURNING id, gateway, amount, currency, status, gateway_transaction_id, created_at, updated_at
            """,
            ctx.tenant_id,
            body.gateway.value,
            body.amount,
            body.currency,
            body.description,
            order_id,
            gw_txn_id,
            body.invoice_id,
        )
    
    res = payment_row_to_out(row)
    res.gateway_url = init_data.get("gateway_url")
    return res


@router.post("/ipn/{gateway}")
async def handle_ipn(
    request: Request,
    gateway: PaymentGateway,
    settings: SettingsDep,
    tenant: str = Query(
        ...,
        description="Tenant subdomain — include in the gateway webhook URL (e.g. ?tenant=demo).",
    ),
):
    """
    Webhook for payment gateways. Supports JSON or form bodies (SSLCommerz uses form posts).
    Register URL like: POST /v1/tenant/payments/ipn/sslcommerz?tenant=demo
    """
    # Parse body before DB so gateways' form posts are validated even if the pool is down (tests + fail-fast).
    ipn_data = await _ipn_payload_dict(request)
    pool = _pool(request)
    sub = tenant.strip().lower()
    tenant_info = await resolve_tenant_id(pool, sub)
    tenant_id = tenant_info["id"]
    tenant_settings = await get_tenant_settings(request, tenant_id)
    
    gw = get_gateway(gateway, settings)
    verified_data = await gw.verify_ipn(ipn_data, settings, tenant_settings)
    if verified_data is None:
        raise HTTPException(status_code=400, detail="Invalid IPN")

    order_ref, gw_txn_id = _ipn_refs(gateway, verified_data)
    if not order_ref and not gw_txn_id:
        raise HTTPException(status_code=400, detail="Verified payment is missing order/transaction reference")

    ipn_amount = _decimal_or_none(verified_data.get("amount"))
    new_status = gw.ipn_payment_status(verified_data)
    if new_status != "completed":
        raise HTTPException(status_code=400, detail="Provider did not verify a successful payment")
    if new_status == "completed" and ipn_amount is None:
        raise HTTPException(status_code=400, detail="Verified payment is missing its amount")

    async with tenant_transaction(request, tenant_id, tenant_info["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, amount, currency, status, gateway_transaction_id, order_id, invoice_id
            FROM tenant_data.payments
            WHERE gateway = $1::text
              AND (
                (
                    $1::text = 'sslcommerz'
                    AND $2::text IS NOT NULL
                    AND order_id = $2
                )
                OR (
                    $1::text <> 'sslcommerz'
                    AND (
                        (
                            $3::text IS NOT NULL
                            AND gateway_transaction_id = $3
                            AND ($2::text IS NULL OR order_id = $2)
                        )
                        OR (
                            $3::text IS NULL
                            AND $2::text IS NOT NULL
                            AND order_id = $2
                        )
                    )
                )
              )
            ORDER BY created_at DESC
            LIMIT 1
            FOR UPDATE
            """,
            gateway.value,
            order_ref or None,
            gw_txn_id or None,
        )
        if not row:
            return {"status": "noop", "reason": "payment_not_found"}

        if row["order_id"] != order_ref:
            raise HTTPException(status_code=400, detail="Verified order does not match payment")
        if row["amount"] != ipn_amount:
            raise HTTPException(status_code=400, detail="Verified amount does not match payment")
        if row["currency"].upper() != str(verified_data.get("currency") or "").upper():
            raise HTTPException(status_code=400, detail="Verified currency does not match payment")
        if row["gateway_transaction_id"] and row["gateway_transaction_id"] != gw_txn_id:
            raise HTTPException(status_code=400, detail="Verified transaction does not match payment")

        if row["status"] == "completed":
            return {"status": "ok", "idempotent": True, "payment_id": str(row["id"])}

        await conn.execute(
            """
            UPDATE tenant_data.payments
            SET status = $2,
                gateway_transaction_id = COALESCE(NULLIF($3::text, ''), gateway_transaction_id),
                ipn_verified = true,
                updated_at = now()
            WHERE id = $1::uuid
            """,
            row["id"],
            new_status,
            gw_txn_id,
        )

    return {"status": "ok", "payment_id": str(row["id"]), "payment_status": new_status}
