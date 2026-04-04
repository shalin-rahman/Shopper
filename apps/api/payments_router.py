from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Query, Request

from config import Settings
from deps import SettingsDep
from redis_client import build_ipn_idempotency_key, ipn_already_processed, ipn_record_processed
from schemas import PaymentCreate, PaymentGateway, PaymentOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction

router = APIRouter(prefix="/v1/tenant/payments", tags=["payments"])


class PaymentGatewayInterface(ABC):
    @abstractmethod
    async def initiate_payment(self, payment: PaymentCreate, tenant_subdomain: str) -> dict[str, Any]:
        pass

    @abstractmethod
    async def verify_ipn(self, ipn_data: dict[str, Any]) -> bool:
        pass

    def ipn_payment_status(self, ipn_data: dict[str, Any]) -> str:
        """Maps gateway payload to tenant_data.payments.status (completed or failed)."""
        return "completed"


class SSLCommerzGateway(PaymentGatewayInterface):
    def __init__(self, settings: Settings):
        self.store_id = settings.sslcommerz_store_id
        self.store_password = settings.sslcommerz_store_password

    async def initiate_payment(self, payment: PaymentCreate, tenant_subdomain: str) -> dict[str, Any]:
        # Placeholder: integrate with SSLCommerz API
        return {"gateway_url": "https://sandbox.sslcommerz.com/gwprocess/v4/api.php", "sessionkey": "test"}

    async def verify_ipn(self, ipn_data: dict[str, Any]) -> bool:
        if self.store_id:
            got = str(ipn_data.get("store_id") or "").strip()
            if got != str(self.store_id).strip():
                return False
        return True

    def ipn_payment_status(self, ipn_data: dict[str, Any]) -> str:
        st = str(ipn_data.get("status") or "").strip().upper()
        return "completed" if st == "VALID" else "failed"


def _get_gateway(gateway: PaymentGateway, settings: Settings) -> PaymentGatewayInterface:
    if gateway == PaymentGateway.sslcommerz:
        return SSLCommerzGateway(settings)
    # Add others as implemented
    raise HTTPException(status_code=501, detail=f"Gateway {gateway} not implemented")


def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
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
async def create_payment(request: Request, body: PaymentCreate, settings: SettingsDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant_id = await resolve_tenant_id(pool, sub)

    gateway = _get_gateway(body.gateway, settings)
    await gateway.initiate_payment(body, sub)

    async with tenant_transaction(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.payments (
                gateway, amount, currency, status, description, order_id
            ) VALUES ($1, $2, $3, 'pending', $4, $5)
            RETURNING id, gateway, amount, currency, status, gateway_transaction_id, created_at, updated_at
            """,
            body.gateway.value,
            body.amount,
            body.currency,
            body.description,
            body.order_id,
        )
    return _row_to_out(row)


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
    tenant_id = await resolve_tenant_id(pool, sub)
    gw = _get_gateway(gateway, settings)
    if not await gw.verify_ipn(ipn_data):
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

    async with tenant_transaction(pool, tenant_id) as conn:
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

    await ipn_record_processed(r, dedupe_key, ttl)
    return {"status": "ok", "payment_id": str(row["id"]), "payment_status": new_status}


def _row_to_out(row: asyncpg.Record) -> PaymentOut:
    d = dict(row)
    if d.get("amount") is not None:
        d["amount"] = Decimal(str(d["amount"]))
    d["gateway"] = PaymentGateway(d["gateway"])
    return PaymentOut(**d)
