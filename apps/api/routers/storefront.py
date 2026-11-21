from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from core.config import Settings
from core.dependencies import SettingsDep
from schemas import StorefrontProductListResponse, StorefrontProductOut, InvoiceOut, InvoiceLineOut, PaymentCreate, PaymentOut
from core.tenant_context import TenantCtxDep
from services.payment_gateway import get_gateway, get_tenant_settings, payment_row_to_out
from services.payment_settlement import reserve_invoice_payment
from services.checkout_link import verify_checkout

router = APIRouter(prefix="/v1/storefront", tags=["storefront"])


@router.api_route("/checkout/return/{result}", methods=["GET", "POST"], include_in_schema=False)
async def checkout_return(result: Literal["success", "fail", "cancel"]):
    # Gateways POST here; the browser then loads the web page on the same host.
    return RedirectResponse(url=f"/checkout/result?status={result}", status_code=303)


@router.get("/products", response_model=StorefrontProductListResponse)
async def storefront_products(
    ctx: TenantCtxDep,
    q: str | None = Query(default=None, max_length=128, description="Filter by SKU or name (substring, case-insensitive)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=50_000),
):
    """Active products for the resolved tenant (public catalog; no buy_price)."""
    pattern = f"%{q}%" if q and q.strip() else None

    async with ctx.transaction() as conn:
        total = await conn.fetchval(
            """
            SELECT count(*)::int
            FROM tenant_data.products p
            WHERE p.is_active = true
              AND p.marketplace_enabled = true
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
              AND p.marketplace_enabled = true
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
    return StorefrontProductListResponse(tenant=ctx.subdomain, products=products, total=int(total or 0))


def _require_checkout_token(ctx, invoice_id: UUID, settings: Settings, t: str | None, e: int | None) -> None:
    if not verify_checkout(ctx.tenant_id, invoice_id, t, e, settings.jwt_secret_key):
        raise HTTPException(status_code=403, detail="Checkout link is invalid or expired")


@router.get("/checkout/{invoice_id}", response_model=InvoiceOut)
async def storefront_invoice_details(
    ctx: TenantCtxDep,
    invoice_id: UUID,
    settings: SettingsDep,
    t: str | None = Query(default=None),
    e: int | None = Query(default=None),
):
    """Public view of an invoice, reached through a signed checkout link."""
    _require_checkout_token(ctx, invoice_id, settings, t, e)
    async with ctx.transaction() as conn:
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
    ctx: TenantCtxDep, 
    invoice_id: UUID, 
    body: PaymentCreate,
    settings: SettingsDep,
    t: str | None = Query(default=None),
    e: int | None = Query(default=None),
):
    """Start a payment session for a specific invoice."""
    _require_checkout_token(ctx, invoice_id, settings, t, e)
    if body.invoice_id is not None and body.invoice_id != invoice_id:
        raise HTTPException(status_code=400, detail="Payment invoice does not match the checkout invoice")

    tenant_settings = await get_tenant_settings(ctx.request, ctx.tenant_id)
    gateway = get_gateway(body.gateway, settings)
    order_id = body.order_id or str(uuid4())
    gateway_body = body.model_copy(
        update={"invoice_id": invoice_id, "order_id": order_id}
    )

    async with ctx.transaction() as conn:
        await reserve_invoice_payment(
            conn,
            invoice_id,
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

        try:
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
                invoice_id,
            )
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=409, detail="A payment with this order or transaction id already exists")
    
    res = payment_row_to_out(row)
    res.gateway_url = init_data.get("gateway_url")
    return res


def _storefront_row(row: asyncpg.Record) -> StorefrontProductOut:
    d = dict(row)
    for k in ("sell_price", "mrp", "vat_rate_pct"):
        if d.get(k) is not None:
            d[k] = Decimal(str(d[k]))
    return StorefrontProductOut(**d)
