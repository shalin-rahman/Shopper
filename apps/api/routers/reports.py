from __future__ import annotations
from collections import Counter
from datetime import date
from decimal import Decimal
import asyncpg
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
import io
import openpyxl
from schemas import (
    InventoryAgingItem, InventoryAgingReportOut, 
    StockValuationItem, StockValuationReportOut,
    VatRegisterLineOut, VatRegisterReportOut,
    BusinessAnalyticsOut
)
from core.tenant_context import TenantCtxDep
from core.dependencies import AccountantDep

router = APIRouter(prefix="/v1/tenant/reports", tags=["reports"])

def _pool(request: Request) -> asyncpg.Pool:
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

@router.get("/business-analytics", response_model=BusinessAnalyticsOut)
async def business_analytics_report(request: Request, _auth: AccountantDep):
    """
    Calculates Inventory Turnover Ratio (ITR) and Economic Order Quantity (EOQ).
    """
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        # COGS calculation (sum of cost of sold items in last 30 days, annualized)
        cogs_30d = await conn.fetchval(
            """
            SELECT COALESCE(SUM(l.qty * l.unit_price), 0)
            FROM tenant_data.invoice_lines l
            JOIN tenant_data.invoices i ON i.id = l.invoice_id
            WHERE i.status = 'paid' AND i.created_at > now() - interval '30 days'
            """
        )
        cogs_annual = Decimal(str(cogs_30d)) * 12

        # Average Inventory Value (simplified: current value)
        avg_inv_value = await conn.fetchval(
            "SELECT COALESCE(SUM(stock_quantity * wac_cost), 1) FROM tenant_data.products WHERE is_active = true"
        )
        avg_inv_value = Decimal(str(avg_inv_value))

        itr = cogs_annual / avg_inv_value

        # EOQ for top 5 moving products
        # D = Annual Demand, S = BDT 500 (fixed order cost), H = 15% of WAC cost (holding cost)
        product_demand = await conn.fetch(
            """
            SELECT p.sku, p.wac_cost, COALESCE(SUM(l.qty), 0) as demand_30d
            FROM tenant_data.products p
            LEFT JOIN tenant_data.invoice_lines l ON l.description_en = p.name_en
            GROUP BY p.sku, p.wac_cost
            ORDER BY demand_30d DESC LIMIT 5
            """
        )

    eoq_list = []
    import math
    for p in product_demand:
        D = float(p['demand_30d']) * 12
        S = 500.0
        H = float(p['wac_cost']) * 0.15
        if H > 0:
            eoq = math.sqrt((2 * D * S) / H)
            eoq_list.append({"sku": p['sku'], "eoq": round(eoq, 2)})

    return BusinessAnalyticsOut(
        inventory_turnover_ratio=itr,
        average_inventory_value=avg_inv_value,
        cogs_annualized=cogs_annual,
        eoq_recommendations=eoq_list
    )

@router.get("/vat-register/export/excel")
async def vat_register_excel_export(
    request: Request, 
    _auth: AccountantDep,
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    """
    Exports Mushak 6.3 Register to Excel.
    """
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(
            "SELECT * FROM tenant_data.vat_sales_register_lines WHERE invoice_date BETWEEN $1 AND $2 ORDER BY invoice_date",
            start_date, end_date
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Mushak 6.3 Register"

    # Header
    headers = ["Invoice No", "Date", "Buyer Name", "TIN", "Description", "Qty", "Taxable Value", "VAT", "Total"]
    ws.append(headers)

    # Data
    for r in rows:
        ws.append([
            r['invoice_no'], r['invoice_date'], r['buyer_name_en'], r['tin'], 
            r['description_en'], float(r['qty']), float(r['taxable_value']), 
            float(r['vat_amount']), float(r['total_amount'])
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"mushak_6_3_register_{start_date}_to_{end_date}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/mushak-6-10", response_model=VatRegisterReportOut)
async def mushak_6_10_report(
    request: Request, 
    _auth: AccountantDep,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000)
):
    """
    NBR Mushak 6.10: Monthly report for transactions >= BDT 200,000.
    """
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(
            """
            SELECT i.invoice_no, i.created_at::date as invoice_date, 
                   c.name_en as buyer_name_en, 
                   SUM(l.qty) as total_qty, 
                   i.subtotal as total_taxable, 
                   i.total_vat as total_vat, 
                   i.total_amount as total_gross
            FROM tenant_data.invoices i
            JOIN tenant_data.customers c ON i.customer_id = c.id
            JOIN tenant_data.invoice_lines l ON l.invoice_id = i.id
            WHERE EXTRACT(MONTH FROM i.created_at) = $1 
              AND EXTRACT(YEAR FROM i.created_at) = $2
              AND i.total_amount >= 200000
            GROUP BY i.id, i.invoice_no, i.created_at, c.name_en, i.subtotal, i.total_vat, i.total_amount
            ORDER BY i.created_at DESC
            """,
            month, year
        )

    lines = [
        VatRegisterLineOut(
            invoice_no=r['invoice_no'],
            invoice_date=r['invoice_date'],
            buyer_name_en=r['buyer_name_en'],
            qty=Decimal(str(r['total_qty'])),
            taxable_value=Decimal(str(r['total_taxable'])),
            vat_amount=Decimal(str(r['total_vat'])),
            total_amount=Decimal(str(r['total_gross']))
        ) for r in rows
    ]

    return VatRegisterReportOut(
        start_date=date(year, month, 1),
        end_date=date(year, month, 28), # Approximated for model response
        total_taxable_value=sum(l.taxable_value for l in lines) if lines else Decimal("0"),
        total_vat_amount=sum(l.vat_amount for l in lines) if lines else Decimal("0"),
        lines=lines
    )


@router.get("/mushak-6-1", response_model=VatRegisterReportOut)
async def mushak_6_1_report(
    request: Request, 
    _auth: AccountantDep,
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    """
    NBR Mushak 6.1: Monthly Purchase Register.
    """
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(
            """
            SELECT po.po_no as invoice_no, po.created_at::date as invoice_date, 
                   s.name_en as buyer_name_en, 
                   SUM(l.qty) as total_qty, 
                   SUM(l.line_total) as total_taxable, 
                   0 as total_vat, 
                   SUM(l.line_total) as total_gross
            FROM tenant_data.purchase_orders po
            JOIN tenant_data.suppliers s ON po.supplier_id = s.id
            JOIN tenant_data.po_lines l ON l.po_id = po.id
            WHERE po.created_at::date BETWEEN $1 AND $2
            GROUP BY po.id, po.po_no, po.created_at, s.name_en
            ORDER BY po.created_at DESC
            """,
            start_date, end_date
        )

    lines = [
        VatRegisterLineOut(
            invoice_no=r['invoice_no'],
            invoice_date=r['invoice_date'],
            buyer_name_en=r['buyer_name_en'],
            qty=Decimal(str(r['total_qty'])),
            taxable_value=Decimal(str(r['total_taxable'])),
            vat_amount=Decimal(str(r['total_vat'])),
            total_amount=Decimal(str(r['total_gross']))
        ) for r in rows
    ]

    return VatRegisterReportOut(
        start_date=start_date,
        end_date=end_date,
        total_taxable_value=sum(l.taxable_value for l in lines) if lines else Decimal("0"),
        total_vat_amount=sum(l.vat_amount for l in lines) if lines else Decimal("0"),
        lines=lines
    )
