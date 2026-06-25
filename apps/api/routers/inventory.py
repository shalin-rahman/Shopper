from __future__ import annotations
from decimal import Decimal
from uuid import UUID
import io
import asyncpg
from fastapi import APIRouter, HTTPException, Query, Request, Response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

from core.tenant_context import TenantCtxDep
from core.dependencies import StaffDep

router = APIRouter(prefix="/v1/tenant/inventory", tags=["inventory"])

@router.post("/receive", status_code=201)
async def stock_receive(request: Request, body: dict, _auth: StaffDep):
    """
    Increases stock. Reasons: purchase, gift_in, return_in.
    """
    sub = subdomain_from_request(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    sku = body.get("sku")
    qty = Decimal(str(body.get("qty", 0)))
    tx_type = body.get("type", "receive") # receive, gift_in, return_in
    unit_cost = body.get("unit_cost")
    
    if not sku or qty <= 0:
        raise HTTPException(status_code=400, detail="Missing required SKU or Qty")

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        tx = await conn.fetchrow(
            """
            INSERT INTO tenant_data.stock_transactions (
                product_id, transaction_type, quantity, unit_cost, notes, reason_code
            ) 
            SELECT id, $1, $2, $3, $4, $5 
            FROM tenant_data.products WHERE sku = $6
            RETURNING *
            """,
            tx_type, qty, unit_cost, body.get("notes"), body.get("reason_code"), sku
        )
        if not tx:
            raise HTTPException(status_code=404, detail="Product SKU not found")
        return {"id": tx["id"], "type": tx_type, "status": "recorded"}

@router.post("/adjust", status_code=201)
async def stock_adjust(request: Request, body: dict, _auth: StaffDep):
    """
    Decreases stock. Reasons: damage, return_out, gift_out, expired.
    """
    sub = subdomain_from_request(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    sku = body.get("sku")
    qty = Decimal(str(body.get("qty", 0)))
    tx_type = body.get("type", "damage") # damage, return_out, gift_out, expired
    
    if not sku or qty <= 0:
        raise HTTPException(status_code=400, detail="Missing required SKU or Qty")

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        tx = await conn.fetchrow(
            """
            INSERT INTO tenant_data.stock_transactions (
                product_id, transaction_type, quantity, notes, reason_code
            ) 
            SELECT id, $1, $2, $3, $4 
            FROM tenant_data.products WHERE sku = $5
            RETURNING *
            """,
            tx_type, -qty, body.get("notes"), body.get("reason_code"), sku
        )
        if not tx:
            raise HTTPException(status_code=404, detail="Product SKU not found")
        return {"id": tx["id"], "type": tx_type, "status": "recorded"}

@router.post("/transfer", status_code=201)
async def create_stock_transfer(request: Request, body: dict, _auth: StaffDep):
    """
    Records a stock transfer between branches and returns Mushak 6.5 info.
    """
    sub = subdomain_from_request(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    sku = body.get("sku")
    qty = Decimal(str(body.get("qty", 0)))
    from_loc = body.get("from_location", "Main Warehouse")
    to_loc = body.get("to_location")
    
    if not sku or qty <= 0 or not to_loc:
        raise HTTPException(status_code=400, detail="Missing required transfer fields")

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        tx = await conn.fetchrow(
            """
            INSERT INTO tenant_data.stock_transactions (
                product_id, transaction_type, quantity, reference_id, notes
            ) 
            SELECT id, 'out', $1, NULL, $2 
            FROM tenant_data.products WHERE sku = $3
            RETURNING *
            """,
            -qty,
            f"Transfer to {to_loc}",
            sku
        )
        if not tx:
            raise HTTPException(status_code=404, detail="Product SKU not found")
        return {"id": tx["id"], "mushak_form": "6.5", "status": "recorded"}

@router.get("/transfer/{tx_id}/mushak-6-5", responses={200: {"content": {"application/pdf": {}}}})
async def get_mushak_6_5_pdf(request: Request, tx_id: UUID, _auth: StaffDep):
    sub = subdomain_from_request(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        tx = await conn.fetchrow(
            """
            SELECT tx.*, p.name_en, p.sku, p.unit
            FROM tenant_data.stock_transactions tx
            JOIN tenant_data.products p ON tx.product_id = p.id
            WHERE tx.id = $1
            """,
            tx_id
        )
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        settings = await conn.fetchrow("SELECT * FROM platform.tenant_settings WHERE tenant_id = $1", tenant_id)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    
    # Mushak 6.5 Header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, height - 1*inch, "Government of the People's Republic of Bangladesh")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 1.2*inch, "National Board of Revenue")
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 1.6*inch, "Mushak 6.5 - Challan for Transfer of Goods")

    c.setFont("Helvetica", 10)
    c.drawRightString(width - 1*inch, height - 2*inch, f"Date: {tx['created_at'].strftime('%Y-%m-%d')}")
    c.drawString(1*inch, height - 2*inch, f"BIN: {settings['bin'] if settings else 'N/A'}")
    c.drawString(1*inch, height - 2.2*inch, f"Registered Name: {settings['legal_title_en'] if settings else sub}")

    # Transfer Details
    c.rect(1*inch, height - 4*inch, width - 2*inch, 1.5*inch)
    c.drawString(1.2*inch, height - 2.8*inch, f"Product SKU: {tx['sku']}")
    c.drawString(1.2*inch, height - 3.0*inch, f"Description: {tx['name_en']}")
    c.drawString(1.2*inch, height - 3.2*inch, f"Quantity: {abs(tx['qty'])} {tx['unit']}")
    c.drawString(1.2*inch, height - 3.4*inch, f"Source: Main Warehouse")
    c.drawString(1.2*inch, height - 3.6*inch, f"Destination: {tx['notes']}")

    c.drawString(1*inch, height - 4.5*inch, "Signature of Issuing Officer:")
    c.line(1*inch, height - 5*inch, 3*inch, height - 5*inch)
    
    c.showPage()
    c.save()
    
    return Response(content=buf.getvalue(), media_type="application/pdf")

@router.get("/history", status_code=200)
async def get_inventory_history(request: Request, _auth: StaffDep):
    """
    Returns full history of stock transactions for auditing.
    """
    sub = subdomain_from_request(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(
            """
            SELECT tx.*, p.sku, p.name_en, p.name_bn
            FROM tenant_data.stock_transactions tx
            JOIN tenant_data.products p ON tx.product_id = p.id
            ORDER BY tx.created_at DESC
            LIMIT 100
            """
        )
        return [dict(r) for r in rows]
