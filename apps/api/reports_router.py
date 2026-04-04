from __future__ import annotations

from datetime import date
from typing import List
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from schemas import ProductOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction

router = APIRouter(prefix="/v1/tenant/reports", tags=["reports"])


def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


@router.get("/inventory-aging")
async def inventory_aging_report(request: Request, as_of: date | None = None):
    """Placeholder: inventory aging report."""
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant_id = await resolve_tenant_id(pool, sub)
    async with tenant_transaction(pool, tenant_id) as conn:
        # Placeholder query
        rows = await conn.fetch(
            """
            SELECT p.sku, p.name_en, p.sell_price
            FROM tenant_data.products p
            WHERE p.is_active = true
            ORDER BY p.sku
            """
        )
    return {"items": [dict(r) for r in rows]}