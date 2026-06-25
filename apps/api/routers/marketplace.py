from __future__ import annotations

from decimal import Decimal
import asyncpg
from fastapi import APIRouter, HTTPException, Query, Request

from core.config import Settings
from core.dependencies import SettingsDep
from schemas import StorefrontProductListResponse, StorefrontProductOut

router = APIRouter(prefix="/v1/marketplace", tags=["marketplace"])

def _pool(request: Request) -> asyncpg.Pool:
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool

@router.get("/search", response_model=StorefrontProductListResponse)
async def global_product_search(
    request: Request,
    q: str | None = Query(default=None, max_length=128, description="Filter by SKU or name across all stores"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=50_000),
):
    """
    Public Aggregator API: Queries ALL active products from ALL active tenants.
    Acts as the backend for the publicportal.org marketplace.
    """
    pool = _pool(request)
    pattern = f"%{q}%" if q and q.strip() else None

    # In a fully scaled multi-DB setup, this would query an Elasticsearch / Redis index.
    # For our RLS-based multi-tenant silo, we can bypass RLS using the platform pool directly
    # to query all records, joining with active platform.tenants.

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            """
            SELECT count(*)::int
            FROM tenant_data.products p
            JOIN platform.tenants t ON p.tenant_id = t.id
            WHERE p.is_active = true AND t.status = 'active'
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
            SELECT 
                p.id, p.sku, p.name_en, p.name_bn, p.description_en, p.description_bn,
                p.unit, p.sell_price, p.mrp, p.vat_rate_pct, p.barcode, p.qr_payload,
                t.subdomain as tenant_subdomain
            FROM tenant_data.products p
            JOIN platform.tenants t ON p.tenant_id = t.id
            WHERE p.is_active = true AND t.status = 'active'
              AND (
                $3::text IS NULL
                OR p.sku ILIKE $3
                OR p.name_en ILIKE $3
                OR p.name_bn ILIKE $3
              )
            ORDER BY p.created_at DESC, p.sku
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
            pattern,
        )

    products = []
    for r in rows:
        d = dict(r)
        # StorefrontProductOut expects strict schemas.
        # We append the tenant_subdomain dynamically for the aggregator UI to link out.
        for k in ("sell_price", "mrp", "vat_rate_pct"):
            if d.get(k) is not None:
                d[k] = Decimal(str(d[k]))
        prod = StorefrontProductOut(**d)
        prod_dict = prod.model_dump()
        prod_dict["tenant_subdomain"] = d["tenant_subdomain"]
        products.append(prod_dict)

    return StorefrontProductListResponse(
        tenant="global-marketplace", 
        products=products, # type: ignore (Allowing the extra field downstream)
        total=int(total or 0)
    )
