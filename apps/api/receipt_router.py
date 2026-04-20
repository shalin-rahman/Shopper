from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, Response, Query
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from deps import StaffDep

router = APIRouter(prefix="/v1/tenant/receipts", tags=["pos"])

@router.get("/{invoice_id}")
async def get_thermal_receipt(
    request: Request, 
    invoice_id: UUID, 
    _auth: StaffDep,
    lang: str = Query("en", regex="^(en|bn)$")
):
    """
    Generates a bilingual Mushak 6.3 receipt for thermal printers (80mm).
    """
    sub = subdomain_from_request(request)
    pool = request.app.state.db_pool
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        inv = await conn.fetchrow(
            """
            SELECT i.*, c.name_en as cust_en, c.name_bn as cust_bn, c.phone as cust_phone
            FROM tenant_data.invoices i
            LEFT JOIN tenant_data.customers c ON i.customer_id = c.id
            WHERE i.id = $1
            """, 
            invoice_id
        )
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        lines = await conn.fetch(
            """
            SELECT l.*, p.name_en, p.name_bn 
            FROM tenant_data.invoice_lines l
            LEFT JOIN tenant_data.products p ON l.product_id = p.id
            WHERE l.invoice_id = $1
            """, 
            invoice_id
        )
        tenant_settings = await conn.fetchrow("SELECT * FROM platform.tenant_settings WHERE tenant_id = $1", tenant_id)

    cols = 42 # 80mm standard
    is_bn = lang == "bn"
    res = []
    
    # 1. Header
    title = (tenant_settings['legal_title_bn' if is_bn else 'legal_title_en'] 
             or tenant_settings['legal_title_en'] or sub)
    res.append(title.center(cols))
    
    if tenant_settings and tenant_settings.get('bin'):
        bin_label = "বিআইএন:" if is_bn else "BIN:"
        res.append(f"{bin_label} {tenant_settings['bin']}".center(cols))
        
    mushak_title = "মূসক ৬.৩ - কর চালান" if is_bn else "Mushak 6.3 - Tax Invoice"
    res.append(mushak_title.center(cols))
    res.append("-" * cols)
    
    # 2. Invoice Meta
    inv_label = "চালান নং:" if is_bn else "Inv:"
    date_label = "তারিখ:" if is_bn else "Date:"
    res.append(f"{inv_label} {inv['invoice_no']}")
    res.append(f"{date_label} {inv['created_at'].strftime('%Y-%m-%d %H:%M')}")
    
    if inv.get('cust_en') or inv.get('cust_bn'):
        cust_name = inv['cust_bn'] if is_bn and inv['cust_bn'] else inv['cust_en']
        res.append(f"{'গ্রাহক' if is_bn else 'Cust'}: {cust_name}")

    res.append("-" * cols)
    
    # 3. Items Header
    if is_bn:
        res.append("বিবরণ          পরিমাণ      মূল্য      মোট")
    else:
        res.append("Item           Qty       Price     Total")
    res.append("-" * cols)
    
    # 4. Items
    for line in lines:
        name = line['name_bn'] if is_bn and line['name_bn'] else line['name_en']
        if not name: name = line['description']
        
        # Multi-line item name support
        name_str = str(name)
        if len(name_str) > 14:
            res.append(name_str)
            name_display = ""
        else:
            name_display = name_str.ljust(14)
            
        qty = str(int(line['qty'])).rjust(5)
        price = f"{line['unit_price']:.0f}".rjust(9)
        total = f"{line['line_total']:.0f}".rjust(10)
        
        if name_display:
            res.append(f"{name_display} {qty} {price} {total}")
        else:
            res.append(f"{' ' * 14} {qty} {price} {total}")

    res.append("-" * cols)
    
    # 5. Totals
    def add_total(label_en, label_bn, value):
        label = label_bn if is_bn else label_en
        res.append(f"{label.ljust(25)} {value:>16.2f}")

    add_total("SUBTOTAL:", "সাবটোটাল:", inv['subtotal'])
    add_total("TOTAL VAT:", "মোট মূসক:", inv['total_vat'])
    add_total("TOTAL:", "সর্বমোট:", inv['total_amount'])
    res.append("-" * cols)
    add_total("PAID:", "পরিশোধিত:", inv['amount_paid'])
    add_total("DUE:", "বকেয়া:", inv['balance_due'])
    
    res.append("-" * cols)
    footer = "কেনাকাটার জন্য ধন্যবাদ!" if is_bn else "Thank you for shopping!"
    res.append(footer.center(cols))
    res.append("-" * cols)
    res.append("\n\n\n")

    return Response(content="\n".join(res), media_type="text/plain; charset=utf-8")
