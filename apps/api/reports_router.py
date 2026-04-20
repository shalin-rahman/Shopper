from __future__ import annotations
from collections import Counter
from datetime import date
from decimal import Decimal
import asyncpg
from fastapi import APIRouter, HTTPException, Request, Query
from schemas import (
    InventoryAgingItem, InventoryAgingReportOut, 
    StockValuationItem, StockValuationReportOut,
    VatRegisterLineOut, VatRegisterReportOut
)
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from deps import AccountantDep

router = APIRouter(prefix="/v1/tenant/reports", tags=["reports"])

def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None: raise HTTPException(status_code=503, detail="Database unavailable")
    return pool

@router.get("/inventory-aging", response_model=InventoryAgingReportOut)
async def inventory_aging_report(request: Request, _auth: AccountantDep, as_of: date | None = None):
    sub = subdomain_from_request(request)
    as_of_d = as_of or date.today()
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(
            """
            WITH last_stock AS (
                SELECT product_id, MAX(created_at)::date AS d
                FROM tenant_data.stock_transactions
                GROUP BY product_id
            )
            SELECT p.sku, p.name_en, p.name_bn, p.unit, p.sell_price,
                COALESCE(ls.d, p.created_at::date) AS reference_date,
                GREATEST(0, ($1::date - COALESCE(ls.d, p.created_at::date)))::int AS days_idle,
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

    items = []
    for r in rows:
        d = dict(r)
        if d.get("sell_price") is not None: d["sell_price"] = Decimal(str(d["sell_price"]))
        items.append(InventoryAgingItem(**d))

    summary = Counter(i.bucket for i in items)
    return InventoryAgingReportOut(
        as_of=as_of_d,
        items=items,
        summary={k: summary[k] for k in ("0_30", "31_60", "61_90", "90_plus")},
    )

@router.get("/stock-valuation", response_model=StockValuationReportOut)
async def stock_valuation_report(request: Request, _auth: AccountantDep):
    """
    Returns inventory value based on Weighted Average Cost (WAC).
    """
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(
            """
            SELECT sku, name_en, name_bn, stock_quantity, wac_cost,
                   (stock_quantity * wac_cost) as total_value
            FROM tenant_data.products
            WHERE is_active = true AND stock_quantity > 0
            ORDER BY total_value DESC
            """
        )
    
    items = []
    total_inv_value = Decimal("0")
    for r in rows:
        items.append(StockValuationItem(
            sku=r['sku'],
            name_en=r['name_en'],
            name_bn=r['name_bn'],
            stock_quantity=Decimal(str(r['stock_quantity'])),
            wac_cost=Decimal(str(r['wac_cost'])),
            total_value=Decimal(str(r['total_value']))
        ))
        total_inv_value += Decimal(str(r['total_value']))
    
    return StockValuationReportOut(total_inventory_value=total_inv_value, items=items)

@router.get("/vat-register", response_model=VatRegisterReportOut)
async def vat_register_report(
    request: Request, 
    _auth: AccountantDep,
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    """
    Summarized Mushak 6.3 VAT Sales Register.
    """
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(
            """
            SELECT invoice_no, invoice_date, buyer_name_en, 
                   SUM(qty) as total_qty, 
                   SUM(taxable_value) as total_taxable, 
                   SUM(vat_amount) as total_vat, 
                   SUM(total_amount) as total_gross
            FROM tenant_data.vat_sales_register_lines
            WHERE invoice_date BETWEEN $1 AND $2
            GROUP BY invoice_no, invoice_date, buyer_name_en
            ORDER BY invoice_date DESC, invoice_no DESC
            """,
            start_date, end_date
        )

    lines = []
    grand_taxable = Decimal("0")
    grand_vat = Decimal("0")
    for r in rows:
        lines.append(VatRegisterLineOut(
            invoice_no=r['invoice_no'],
            invoice_date=r['invoice_date'],
            buyer_name_en=r['buyer_name_en'],
            qty=Decimal(str(r['total_qty'])),
            taxable_value=Decimal(str(r['total_taxable'])),
            vat_amount=Decimal(str(r['total_vat'])),
            total_amount=Decimal(str(r['total_gross']))
        ))
        grand_taxable += Decimal(str(r['total_taxable']))
        grand_vat += Decimal(str(r['total_vat']))

    return VatRegisterReportOut(
        start_date=start_date,
        end_date=end_date,
        total_taxable_value=grand_taxable,
        total_vat_amount=grand_vat,
        lines=lines
    )
