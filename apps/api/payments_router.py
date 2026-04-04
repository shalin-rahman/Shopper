from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from config import Settings
from deps import SettingsDep
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


class SSLCommerzGateway(PaymentGatewayInterface):
    def __init__(self, settings: Settings):
        self.store_id = settings.sslcommerz_store_id
        self.store_password = settings.sslcommerz_store_password

    async def initiate_payment(self, payment: PaymentCreate, tenant_subdomain: str) -> dict[str, Any]:
        # Placeholder: integrate with SSLCommerz API
        return {"gateway_url": "https://sandbox.sslcommerz.com/gwprocess/v4/api.php", "sessionkey": "test"}

    async def verify_ipn(self, ipn_data: dict[str, Any]) -> bool:
        # Placeholder: verify signature
        return True


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


@router.post("", response_model=PaymentOut, status_code=201)
async def create_payment(request: Request, body: PaymentCreate, settings: SettingsDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant_id = await resolve_tenant_id(pool, sub)

    gateway = _get_gateway(body.gateway, settings)
    gateway_response = await gateway.initiate_payment(body, sub)

    async with tenant_transaction(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.payments (
                gateway, amount, currency, status, description, order_id
            ) VALUES ($1, $2, $3, 'pending', $4, $5)
            RETURNING id, gateway, amount, currency, status, gateway_transaction_id, created_at, updated_at
            """,
            body.gateway,
            body.amount,
            body.currency,
            body.description,
            body.order_id,
        )
    return _row_to_out(row)


@router.post("/ipn/{gateway}")
async def handle_ipn(request: Request, gateway: PaymentGateway, settings: SettingsDep):
    # Placeholder: parse IPN data, verify signature, update payment status
    ipn_data = await request.json()
    gw = _get_gateway(gateway, settings)
    if not await gw.verify_ipn(ipn_data):
        raise HTTPException(status_code=400, detail="Invalid IPN")

    # Update payment in DB based on IPN
    # For now, just return success
    return {"status": "ok"}


def _row_to_out(row: asyncpg.Record) -> PaymentOut:
    d = dict(row)
    if d.get("amount") is not None:
        d["amount"] = Decimal(str(d["amount"]))
    return PaymentOut(**d)