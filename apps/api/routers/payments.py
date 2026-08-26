from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Query, Request

from core.config import Settings
from core.dependencies import SettingsDep, StaffDep
from redis_client import build_ipn_idempotency_key, ipn_already_processed, ipn_record_processed
from schemas import PaymentCreate, PaymentGateway, PaymentOut
from core.tenant_context import TenantCtxDep
from services.payment_gateway import get_gateway, get_tenant_settings, payment_row_to_out, PaymentGatewayInterface

router = APIRouter(prefix="/v1/tenant/payments", tags=["payments"])

def _pool(request: Request) -> asyncpg.Pool:
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


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
        str(data.get("order_id") or data.get("merchantInvoiceNumber") or "").strip(),
        str(
            data.get("transaction_id")
            or data.get("paymentID")
            or data.get("val_id")
            or ""
        ).strip(),
    )


@router.post("", response_model=PaymentOut, status_code=201)
async def create_payment(ctx: TenantCtxDep, body: PaymentCreate, settings: SettingsDep, _auth: StaffDep):
    tenant_settings = await get_tenant_settings(ctx.request, ctx.tenant_id)

    gateway = get_gateway(body.gateway, settings)
    init_data = await gateway.initiate_payment(body, ctx.subdomain, settings, tenant_settings)

    # Use gateway_transaction_id if returned (bKash returns paymentID here)
    gw_txn_id = init_data.get("paymentID") or init_data.get("gateway_transaction_id")

    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.payments (
                gateway, amount, currency, status, description, order_id, gateway_transaction_id
            ) VALUES ($1, $2, $3, 'pending', $4, $5, $6)
            RETURNING id, gateway, amount, currency, status, gateway_transaction_id, created_at, updated_at
            """,
            body.gateway.value,
            body.amount,
            body.currency,
            body.description,
            body.order_id,
            gw_txn_id,
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
    if not await gw.verify_ipn(ipn_data, settings, tenant_settings):
        raise HTTPException(status_code=400, detail="Invalid IPN")

    order_ref, gw_txn_id = _ipn_refs(gateway, ipn_data)
    if not order_ref and not gw_txn_id:
        raise HTTPException(status_code=400, detail="IPN missing order/transaction reference")

    r = getattr(request.app.state, "redis", None)
    ttl = settings.redis_ipn_ttl_seconds
    if ttl <= 0:
        ttl = 86_400
    dedupe_key = build_ipn_idempotency_key(sub, gateway.value, order_ref, gw_txn_id)
    if await ipn_already_processed(r, dedupe_key):
        return {"status": "ok", "idempotent": True, "source": "redis"}

    ipn_amount = _decimal_or_none(ipn_data.get("amount"))
    new_status = gw.ipn_payment_status(ipn_data)
    if new_status not in ("completed", "failed"):
        new_status = "failed"

    async with tenant_transaction(request, tenant_id, tenant_info["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, amount, status, gateway_transaction_id, order_id
            FROM tenant_data.payments
            WHERE gateway = $1::text
              AND (
                ($2::text IS NOT NULL AND $2 <> '' AND order_id = $2)
                OR ($3::text IS NOT NULL AND $3 <> '' AND gateway_transaction_id = $3)
              )
            ORDER BY created_at DESC
            LIMIT 1
            """,
            gateway.value,
            order_ref or None,
            gw_txn_id or None,
        )
        if not row:
            return {"status": "noop", "reason": "payment_not_found"}

        if ipn_amount is not None and row["amount"] != ipn_amount:
            raise HTTPException(status_code=400, detail="IPN amount does not match payment")

        if row["status"] == "completed" and new_status == "completed":
            await ipn_record_processed(r, dedupe_key, ttl)
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
        # If this payment is linked to an invoice, update the invoice totals
        if row.get('invoice_id'):
            invoice_id = row['invoice_id']
            # Fetch current invoice data
            inv = await conn.fetchrow(
                """
                SELECT id, subtotal, total_vat, total_amount, amount_paid, balance_due, status
                FROM tenant_data.invoices
                WHERE id = $1
                """,
                invoice_id,
            )
            if inv:
                # Calculate new paid amount and balance
                paid = (inv['amount_paid'] or Decimal('0')) + row['amount']
                balance = (inv['total_amount'] or Decimal('0')) - paid
                new_inv_status = 'paid' if balance <= 0 else 'partially_paid'
                await conn.execute(
                    """
                    UPDATE tenant_data.invoices
                    SET amount_paid = $2,
                        balance_due = $3,
                        status = $4,
                        updated_at = now()
                    WHERE id = $1
                    """,
                    invoice_id,
                    paid,
                    balance,
                    new_inv_status,
                )

    await ipn_record_processed(r, dedupe_key, ttl)
    return {"status": "ok", "payment_id": str(row["id"]), "payment_status": new_status}
