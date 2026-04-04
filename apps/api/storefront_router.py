from __future__ import annotations

from decimal import Decimal

import asyncpg
from fastapi import APIRouter, HTTPException, Query, Request

from schemas import StorefrontProductListResponse, StorefrontProductOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction

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
    await resolve_tenant_id(pool, sub)

    pattern = f"%{q}%" if q and q.strip() else None

    async with tenant_transaction(pool, tenant_id) as conn:
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


def _storefront_row(row: asyncpg.Record) -> StorefrontProductOut:
    d = dict(row)
    for k in ("sell_price", "mrp", "vat_rate_pct"):
        if d.get(k) is not None:
            d[k] = Decimal(str(d[k]))
    return StorefrontProductOut(**d)
