from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import io

import asyncpg
import qrcode
from fastapi import APIRouter, HTTPException, Query, Request, Response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

from schemas import InvoiceCreate, InvoiceOut, InvoiceLineOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from deps import StaffDep

router = APIRouter(prefix="/v1/tenant/invoices", tags=["invoices"])


def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


@router.post("", response_model=InvoiceOut, status_code=201)
async def create_invoice(request: Request, body: InvoiceCreate, _auth: StaffDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

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

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        # Create Invoice
        invoice_row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.invoices (
                customer_id, invoice_no, subtotal, total_vat, total_amount, balance_due, status, notes
            ) VALUES ($1, $2, $3, $4, $5, $5, 'draft', $6)
            RETURNING *
            """,
            body.customer_id,
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


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    request: Request,
    _auth: StaffDep,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
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
async def get_invoice(request: Request, id: UUID, _auth: StaffDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
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
async def get_invoice_qr(request: Request, id: UUID, _auth: StaffDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        invoice_row = await conn.fetchrow(
            "SELECT invoice_no, total_amount FROM tenant_data.invoices WHERE id = $1", id
        )
        if not invoice_row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Retrieve merchant IDs from settings to include in QR as per requirements
        settings_row = await conn.fetchrow(
            "SELECT bkash_app_key, nagad_merchant_id FROM platform.tenant_settings WHERE tenant_id = $1",
            tenant_id
        )

    settings = getattr(request.app.state, "settings", None)
    base_url = (settings.storefront_public_base_url if settings else None) or f"https://{sub}.shopper.com"
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
async def get_invoice_mushak_pdf(request: Request, id: UUID, _auth: StaffDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        invoice_row = await conn.fetchrow(
            "SELECT * FROM tenant_data.invoices WHERE id = $1", id
        )
        if not invoice_row:
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        line_rows = await conn.fetch(
            "SELECT * FROM tenant_data.invoice_lines WHERE invoice_id = $1", id
        )
        
        tenant_settings = await conn.fetchrow(
            "SELECT * FROM platform.tenant_settings WHERE tenant_id = $1", tenant_id
        )

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    
    # Header: Mushak 6.3
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2.0, height - 1 * inch, "Mushak 6.3 - Tax Invoice")
    
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 1.5 * inch, f"Invoice No: {invoice_row['invoice_no']}")
    
    tenant_name = tenant_settings['legal_title_en'] if tenant_settings and tenant_settings.get('legal_title_en') else sub
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
