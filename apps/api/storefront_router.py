from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Query, Request

from config import Settings
from deps import SettingsDep
from schemas import StorefrontProductListResponse, StorefrontProductOut, InvoiceOut, InvoiceLineOut, PaymentCreate, PaymentOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from payments_core import get_gateway, get_tenant_settings, payment_row_to_out

router = APIRouter(prefix="/v1/storefront", tags=["storefront"])


def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


@router.get("/products", response_model=StorefrontProductListResponse)
async def storefront_products(
    request: Request,
    q: str | None = Query(default=None, max_length=128, description="Filter by SKU or name (substring, case-insensitive)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=50_000),
):
    """Active products for the resolved tenant (public catalog; no buy_price)."""
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    pattern = f"%{q}%" if q and q.strip() else None

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        total = await conn.fetchval(
            """
            SELECT count(*)::int
            FROM tenant_data.products p
            WHERE p.is_active = true
              AND (
                $1::text IS NULL
                OR p.sku ILIKE $1
                OR p.name_en ILIKE $1
                OR p.name_bn ILIKE $1
              )
            """,
            pattern,
        )
        rows = await conn.fetch(
            """
            SELECT p.id, p.sku, p.name_en, p.name_bn, p.description_en, p.description_bn,
                   p.unit, p.sell_price, p.mrp, p.vat_rate_pct, p.barcode, p.qr_payload
            FROM tenant_data.products p
            WHERE p.is_active = true
              AND (
                $3::text IS NULL
                OR p.sku ILIKE $3
                OR p.name_en ILIKE $3
                OR p.name_bn ILIKE $3
              )
            ORDER BY p.sku
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
            pattern,
        )

    products = [_storefront_row(r) for r in rows]
    return StorefrontProductListResponse(tenant=sub, products=products, total=int(total or 0))


@router.get("/checkout/{invoice_id}", response_model=InvoiceOut)
async def storefront_invoice_details(request: Request, invoice_id: UUID):
    """Public view of an invoice (e.g. for customer payment)."""
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            """
            SELECT i.*
            FROM tenant_data.invoices i
            WHERE i.id = $1
            """,
            invoice_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        lines = await conn.fetch(
            """
            SELECT * FROM tenant_data.invoice_lines WHERE invoice_id = $1 ORDER BY id
            """,
            invoice_id,
        )
    
    res = dict(row)
    res['lines'] = [dict(l) for l in lines]
    return InvoiceOut(**res)


@router.post("/checkout/{invoice_id}/pay", response_model=PaymentOut, status_code=201)
async def storefront_initiate_payment(
    request: Request, 
    invoice_id: UUID, 
    body: PaymentCreate, 
    settings: SettingsDep
):
    """Start a payment session for a specific invoice."""
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    tenant_settings = await get_tenant_settings(request, tenant_id)

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        # 1. Verify invoice exists and has balance
        inv = await conn.fetchrow(
            "SELECT total_amount, balance_due FROM tenant_data.invoices WHERE id = $1",
            invoice_id,
        )
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if inv["balance_due"] <= 0:
            raise HTTPException(status_code=400, detail="Invoice is already fully paid")
        
        if body.amount > inv["balance_due"]:
             raise HTTPException(status_code=400, detail="Payment amount exceeds remaining balance")

        # 2. Initiate gateway
        gateway = get_gateway(body.gateway, settings)
        init_data = await gateway.initiate_payment(body, sub, settings, tenant_settings)
        gw_txn_id = init_data.get("paymentID") or init_data.get("gateway_transaction_id")

        # 3. Record pending payment
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.payments (
                gateway, amount, currency, status, description, order_id, gateway_transaction_id, invoice_id
            ) VALUES ($1, $2, $3, 'pending', $4, $5, $6, $7)
            RETURNING id, gateway, amount, currency, status, gateway_transaction_id, created_at, updated_at
            """,
            body.gateway.value,
            body.amount,
            body.currency,
            body.description,
            body.order_id, # Could be null if not using POS order ref
            gw_txn_id,
            invoice_id,
        )
    
    res = payment_row_to_out(row)
    res.gateway_url = init_data.get("gateway_url")
    return res


def _storefront_row(row: asyncpg.Record) -> StorefrontProductOut:
    d = dict(row)
    for k in ("sell_price", "mrp", "vat_rate_pct"):
        if d.get(k) is not None:
            d[k] = Decimal(str(d[k]))
    return StorefrontProductOut(**d)
