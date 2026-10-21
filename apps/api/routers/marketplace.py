from __future__ import annotations

from decimal import Decimal
import asyncpg
from fastapi import APIRouter, HTTPException, Query, Request

from core.config import Settings
from core.dependencies import SettingsDep
from schemas import StorefrontProductListResponse, StorefrontProductOut

router = APIRouter(prefix="/v1/marketplace", tags=["marketplace"])

def _pool(request: Request) -> asyncpg.Pool:
    pool = getattr(request.app.state, "db_pool", None)
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
    """Search only explicitly opted-in products through the restricted database function."""
    pool = _pool(request)
    pattern = f"%{q}%" if q and q.strip() else None

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            """
            SELECT count(*)::int
            FROM platform.search_public_marketplace_products($1)
            """,
            pattern,
        )
        rows = await conn.fetch(
            """
            SELECT id, sku, name_en, name_bn, description_en, description_bn,
                   unit, sell_price, mrp, vat_rate_pct, tenant_subdomain
            FROM platform.search_public_marketplace_products($3)
            ORDER BY sku, id
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
            pattern,
        )

    products = []
    for r in rows:
        d = dict(r)
        for k in ("sell_price", "mrp", "vat_rate_pct"):
            if d.get(k) is not None:
                d[k] = Decimal(str(d[k]))
        prod = StorefrontProductOut(**d)
        products.append(prod.model_dump())

    return StorefrontProductListResponse(
        tenant="global-marketplace", 
        products=products,
        total=int(total or 0)
    )
