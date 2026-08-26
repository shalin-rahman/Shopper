from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime

import io

import asyncpg
import qrcode
from fastapi import APIRouter, HTTPException, Query, Response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

from schemas import InvoiceCreate, InvoiceOut, InvoiceLineOut, SalesReturnCreate, CreditNoteOut
from core.tenant_context import TenantCtxDep
from core.dependencies import StaffDep

router = APIRouter(prefix="/v1/tenant/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceOut, status_code=201)
async def create_invoice(ctx: TenantCtxDep, body: InvoiceCreate, _auth: StaffDep):
    # 0. Smart Inline Saving of Customer
    customer_id = body.customer_id
    if body.customer_data and not customer_id:
        async with ctx.transaction() as conn:
            # Check if customer code already exists to prevent duplicates
            existing = await conn.fetchval(
                "SELECT id FROM tenant_data.customers WHERE code = $1", 
                body.customer_data.code
            )
            if existing:
                customer_id = existing
            else:
                row = await conn.fetchrow(
                    """
                    INSERT INTO tenant_data.customers (
                        code, name_en, name_bn, phone, email, billing_address_en
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    body.customer_data.code,
                    body.customer_data.name_en,
                    body.customer_data.name_bn,
                    body.customer_data.phone,
                    body.customer_data.email,
                    body.customer_data.billing_address_en
                )
                customer_id = row["id"]

    # 1. Calculate totals
    subtotal = Decimal("0")
    total_vat = Decimal("0")
    processed_lines = []

    for line in body.lines:
        line_subtotal = line.qty * line.unit_price
        line_vat = (line_subtotal * line.vat_rate_pct) / Decimal("100")
        line_total = line_subtotal + line_vat
        
        subtotal += line_subtotal
        total_vat += line_vat
        
        processed_lines.append({
            **line.model_dump(),
            "vat_amount": line_vat,
            "line_total": line_total
        })

    total_amount = subtotal + total_vat

    # High-Value Trigger (BDT 200,000) for Mushak 6.10 compliance
    HIGH_VALUE_THRESHOLD = Decimal("200000")
    if total_amount >= HIGH_VALUE_THRESHOLD:
        if not customer_id:
            raise HTTPException(
                status_code=400, 
                detail="Customer ID is required for high-value invoices (>= 200,000 BDT) for Mushak 6.10 compliance."
            )
        
        async with ctx.transaction() as conn:
            customer = await conn.fetchrow(
                "SELECT tin, nid, bin FROM tenant_data.customers WHERE id = $1", 
                customer_id
            )
            if not customer or not (customer["tin"] or customer["nid"] or customer["bin"]):
                raise HTTPException(
                    status_code=400, 
                    detail="Customer must have a valid TIN, NID, or BIN for high-value invoices per Mushak 6.10 requirements."
                )

    async with ctx.transaction() as conn:
        # Create Invoice
        invoice_row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.invoices (
                customer_id, invoice_no, subtotal, total_vat, total_amount, balance_due, status, notes
            ) VALUES ($1, $2, $3, $4, $5, $5, 'draft', $6)
            RETURNING *
            """,
            customer_id,
            body.invoice_no,
            subtotal,
            total_vat,
            total_amount,
            body.notes
        )
        
        invoice_id = invoice_row["id"]
        
        # Create Lines
        line_rows = []
        for pline in processed_lines:
            lr = await conn.fetchrow(
                """
                INSERT INTO tenant_data.invoice_lines (
                    invoice_id, product_id, description, qty, unit_price, vat_rate_pct, vat_amount, line_total
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                invoice_id,
                pline["product_id"],
                pline["description"],
                pline["qty"],
                pline["unit_price"],
                pline["vat_rate_pct"],
                pline["vat_amount"],
                pline["line_total"]
            )
            line_rows.append(lr)

    return _row_to_out(invoice_row, line_rows)


@router.post("/returns", response_model=CreditNoteOut, status_code=201)
async def create_sales_return(ctx: TenantCtxDep, body: SalesReturnCreate, _auth: StaffDep):
    """
    Creates a Sales Return (Mushak 6.7) and generates a Credit Note.
    Decreases the invoice's balance_due and records stock reversal.
    """
    async with ctx.transaction() as conn:
        # 1. Fetch original invoice
        invoice = await conn.fetchrow(
            "SELECT * FROM tenant_data.invoices WHERE id = $1", body.invoice_id
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # 2. Calculate adjustment (Simplify: use direct items or total from body)
        # For production-grade, we would calculate VAT per returned item.
        # Here we use total returned value derived from items.
        total_taxable = Decimal("0")
        total_vat = Decimal("0")
        
        for item in body.items:
            # Fetch product info for VAT and pricing
            prod = await conn.fetchrow("SELECT sell_price, vat_rate_pct FROM tenant_data.products WHERE id = $1", item["product_id"])
            if prod:
                taxable = Decimal(str(item["qty"])) * Decimal(str(prod["sell_price"]))
                vat = (taxable * Decimal(str(prod["vat_rate_pct"]))) / Decimal("100")
                total_taxable += taxable
                total_vat += vat

        total_adjustment = total_taxable + total_vat
        note_no = f"CN-{datetime.now().strftime('%Y%m%d')}-{body.invoice_id.hex[:4]}"

        # 3. Insert Credit Note (Mushak 6.7)
        cn_row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.credit_notes (
                tenant_id, invoice_id, note_no, reason, 
                adjustment_amount_taxable, adjustment_amount_vat, total_adjustment
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            ctx.tenant_id, body.invoice_id, note_no, body.reason,
            total_taxable, total_vat, total_adjustment
        )

        # 4. Update Invoice Balance
        await conn.execute(
            """
            UPDATE tenant_data.invoices 
            SET total_amount = total_amount - $1, 
                balance_due = balance_due - $1,
                updated_at = now()
            WHERE id = $2
            """,
            total_adjustment, body.invoice_id
        )

        # 5. Reverse Stock for returned items
        for item in body.items:
             await conn.execute(
                """
                INSERT INTO tenant_data.stock_transactions (
                    tenant_id, product_id, transaction_type, quantity, 
                    reference_type, reference_id, notes
                ) VALUES ($1, $2, 'in', $3, 'return', $4, $5)
                """,
                ctx.tenant_id, item["product_id"], item["qty"], 
                cn_row["id"], f"Sales Return: {note_no}"
            )
             
             await conn.execute(
                 "UPDATE tenant_data.products SET stock_quantity = stock_quantity + $1 WHERE id = $2",
                 item["qty"], item["product_id"]
             )

    return CreditNoteOut(**dict(cn_row))


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    ctx: TenantCtxDep,
    _auth: StaffDep,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    async with ctx.transaction() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM tenant_data.invoices
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset
        )
    
    return [_row_to_out(r) for r in rows]


@router.get("/{id}", response_model=InvoiceOut)
async def get_invoice(ctx: TenantCtxDep, id: UUID, _auth: StaffDep):
    async with ctx.transaction() as conn:
        invoice_row = await conn.fetchrow(
            "SELECT * FROM tenant_data.invoices WHERE id = $1", id
        )
        if not invoice_row:
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        line_rows = await conn.fetch(
            "SELECT * FROM tenant_data.invoice_lines WHERE invoice_id = $1", id
        )

    return _row_to_out(invoice_row, line_rows)


@router.get("/{id}/qr", responses={200: {"content": {"image/png": {}}}})
async def get_invoice_qr(ctx: TenantCtxDep, id: UUID, _auth: StaffDep):
    async with ctx.transaction() as conn:
        invoice_row = await conn.fetchrow(
            "SELECT invoice_no, total_amount FROM tenant_data.invoices WHERE id = $1", id
        )
        if not invoice_row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Retrieve merchant IDs from settings to include in QR as per requirements
        settings_row = await conn.fetchrow(
            "SELECT bkash_app_key, nagad_merchant_id FROM platform.tenant_settings WHERE tenant_id = $1",
            ctx.tenant_id
        )

    settings = getattr(ctx.request.app.state, "settings", None)
    base_url = (settings.storefront_public_base_url if settings else None) or f"https://{ctx.subdomain}.shopper.com"
    amount = Decimal(str(invoice_row["total_amount"]))
    invoice_no = invoice_row["invoice_no"]
    
    # Payload conceptually combining amounts and merchant data for generic or MFS scanning
    b_key = settings_row["bkash_app_key"] if settings_row and settings_row["bkash_app_key"] else ""
    n_id = settings_row["nagad_merchant_id"] if settings_row and settings_row["nagad_merchant_id"] else ""
    
    qr_payload = f"{base_url}/checkout?invoice={invoice_no}&amount={amount:.2f}&bkash={b_key}&nagad={n_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/{id}/mushak", responses={200: {"content": {"application/pdf": {}}}})
async def get_invoice_mushak_pdf(ctx: TenantCtxDep, id: UUID, _auth: StaffDep):
    async with ctx.transaction() as conn:
        invoice_row = await conn.fetchrow(
            "SELECT * FROM tenant_data.invoices WHERE id = $1", id
        )
        if not invoice_row:
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        line_rows = await conn.fetch(
            "SELECT * FROM tenant_data.invoice_lines WHERE invoice_id = $1", id
        )
        
        tenant_settings = await conn.fetchrow(
            "SELECT * FROM platform.tenant_settings WHERE tenant_id = $1", ctx.tenant_id
        )

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    
    # Header: Mushak 6.3
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2.0, height - 1 * inch, "Mushak 6.3 - Tax Invoice")
    
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 1.5 * inch, f"Invoice No: {invoice_row['invoice_no']}")
    
    tenant_name = tenant_settings['legal_title_en'] if tenant_settings and tenant_settings.get('legal_title_en') else ctx.subdomain
    c.drawString(1 * inch, height - 1.7 * inch, f"Tenant: {tenant_name}")
    
    bin_num = tenant_settings['bin'] if tenant_settings and tenant_settings.get('bin') else "N/A"
    c.drawString(1 * inch, height - 1.9 * inch, f"BIN: {bin_num}")
    
    # Lines
    y = height - 2.5 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Description")
    c.drawString(4 * inch, y, "Qty")
    c.drawString(5 * inch, y, "Unit Price")
    c.drawString(6 * inch, y, "VAT")
    c.drawString(7 * inch, y, "Total")
    
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    for lr in line_rows:
        c.drawString(1 * inch, y, str(lr['description'])[:30])
        c.drawString(4 * inch, y, str(lr['qty']))
        c.drawString(5 * inch, y, str(lr['unit_price']))
        c.drawString(6 * inch, y, str(lr['vat_amount']))
        c.drawString(7 * inch, y, str(lr['line_total']))
        y -= 0.2 * inch
    
    # Totals
    y -= 0.4 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(4 * inch, y, "Subtotal:")
    c.drawString(6 * inch, y, str(invoice_row['subtotal']))
    
    y -= 0.2 * inch
    c.drawString(4 * inch, y, "Total VAT:")
    c.drawString(6 * inch, y, str(invoice_row['total_vat']))
    
    y -= 0.2 * inch
    c.drawString(4 * inch, y, "Total Amount:")
    c.drawString(6 * inch, y, str(invoice_row['total_amount']))

    y -= 0.2 * inch
    c.drawString(4 * inch, y, "Amount Paid:")
    c.drawString(6 * inch, y, str(invoice_row['amount_paid']))

    y -= 0.2 * inch
    c.drawString(4 * inch, y, "Balance Due:")
    c.drawString(6 * inch, y, str(invoice_row['balance_due']))

    c.showPage()
    c.save()
    
    return Response(content=buf.getvalue(), media_type="application/pdf")


def _row_to_out(invoice_row: asyncpg.Record, line_rows: list[asyncpg.Record] = None) -> InvoiceOut:
    d = dict(invoice_row)
    # Ensure decimals are correctly typed
    for key in ["subtotal", "total_vat", "total_amount", "amount_paid", "balance_due"]:
        if d.get(key) is not None:
            d[key] = Decimal(str(d[key]))
            
    if line_rows:
        lines = []
        for lr in line_rows:
            ld = dict(lr)
            for k in ["qty", "unit_price", "vat_rate_pct", "vat_amount", "line_total"]:
                if ld.get(k) is not None:
                    ld[k] = Decimal(str(ld[k]))
            lines.append(InvoiceLineOut(**ld))
        d["lines"] = lines
    else:
        d["lines"] = []
        
    return InvoiceOut(**d)
