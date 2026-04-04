from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from schemas import InventoryAgingItem, InventoryAgingReportOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction

router = APIRouter(prefix="/v1/tenant/reports", tags=["reports"])


def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


@router.get("/inventory-aging", response_model=InventoryAgingReportOut)
async def inventory_aging_report(request: Request, as_of: date | None = None):
    """
    Days since last stock transaction per active SKU (fallback: product `created_at` date).
    Buckets: 0–30, 31–60, 61–90, 90+ days idle.
    """
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    as_of_d = as_of or date.today()

    pool = _pool(request)
    await resolve_tenant_id(pool, sub)

    async with tenant_transaction(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            WITH last_stock AS (
                SELECT product_id, MAX(created_at)::date AS d
                FROM tenant_data.stock_transactions
                GROUP BY product_id
            )
            SELECT
                p.sku,
                p.name_en,
                p.name_bn,
                p.unit,
                p.sell_price,
                COALESCE(ls.d, p.created_at::date) AS reference_date,
                GREATEST(
                    0,
                    ($1::date - COALESCE(ls.d, p.created_at::date))
                )::int AS days_idle,
                CASE
                    WHEN GREATEST(0, ($1::date - COALESCE(ls.d, p.created_at::date))) <= 30 THEN '0_30'
                    WHEN GREATEST(0, ($1::date - COALESCE(ls.d, p.created_at::date))) <= 60 THEN '31_60'
                    WHEN GREATEST(0, ($1::date - COALESCE(ls.d, p.created_at::date))) <= 90 THEN '61_90'
                    ELSE '90_plus'
                END AS bucket
            FROM tenant_data.products p
            LEFT JOIN last_stock ls ON ls.product_id = p.id
            WHERE p.is_active = true
            ORDER BY days_idle DESC, p.sku
            """,
            as_of_d,
        )

    items: list[InventoryAgingItem] = []
    for r in rows:
        d = dict(r)
        if d.get("sell_price") is not None:
            d["sell_price"] = Decimal(str(d["sell_price"]))
        items.append(InventoryAgingItem(**d))

    summary = Counter(i.bucket for i in items)
    return InventoryAgingReportOut(
        as_of=as_of_d,
        items=items,
        summary={k: summary[k] for k in ("0_30", "31_60", "61_90", "90_plus")},
    )
