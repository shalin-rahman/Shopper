from __future__ import annotations
from decimal import Decimal
from typing import Literal
from uuid import UUID
import io
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

from core.tenant_context import TenantCtxDep
from core.dependencies import StaffDep

router = APIRouter(prefix="/v1/tenant/inventory", tags=["inventory"])


class StockReceiveRequest(BaseModel):
    sku: str = Field(..., min_length=1)
    qty: Decimal = Field(..., gt=0)
    type: Literal["in", "receive", "return_in", "gift_in"] = "receive"
    unit_cost: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    reason_code: str | None = None


class StockAdjustRequest(BaseModel):
    sku: str = Field(..., min_length=1)
    qty: Decimal = Field(..., gt=0)
    type: Literal["out", "damage", "return_out", "gift_out", "expired"] = "damage"
    notes: str | None = None
    reason_code: str | None = None


class StockTransferRequest(BaseModel):
    sku: str = Field(..., min_length=1)
    qty: Decimal = Field(..., gt=0)
    to_location: str = Field(..., min_length=1)
    from_location: str = Field(default="Main Warehouse", min_length=1)


@router.post("/receive", status_code=201)
async def stock_receive(ctx: TenantCtxDep, body: StockReceiveRequest, _auth: StaffDep):
    """
    Increases stock. Reasons: purchase, gift_in, return_in.
    """
    async with ctx.transaction() as conn:
        product = await conn.fetchrow(
            "SELECT id FROM tenant_data.products WHERE sku = $1 AND is_active = true FOR UPDATE",
            body.sku.strip(),
        )
        if not product:
            raise HTTPException(status_code=404, detail="Product SKU not found")

        tx = await conn.fetchrow(
            """
            INSERT INTO tenant_data.stock_transactions (
                tenant_id, product_id, transaction_type, quantity, unit_cost,
                reference_type, notes, reason_code
            ) VALUES ($1, $2, 'in', $3, $4, 'manual', $5, $6)
            RETURNING *
            """,
            ctx.tenant_id,
            product["id"],
            body.qty,
            body.unit_cost,
            body.notes,
            body.reason_code or body.type,
        )
        await conn.execute(
            "UPDATE tenant_data.products SET stock_quantity = stock_quantity + $1 WHERE id = $2",
            body.qty,
            product["id"],
        )
        return {"id": tx["id"], "type": body.type, "status": "recorded"}

@router.post("/adjust", status_code=201)
async def stock_adjust(ctx: TenantCtxDep, body: StockAdjustRequest, _auth: StaffDep):
    """
    Decreases stock. Reasons: damage, return_out, gift_out, expired.
    """
    async with ctx.transaction() as conn:
        product = await conn.fetchrow(
            "SELECT id, stock_quantity FROM tenant_data.products WHERE sku = $1 AND is_active = true FOR UPDATE",
            body.sku.strip(),
        )
        if not product:
            raise HTTPException(status_code=404, detail="Product SKU not found")
        if Decimal(str(product["stock_quantity"])) < body.qty:
            raise HTTPException(status_code=409, detail="Insufficient stock for this adjustment")

        tx = await conn.fetchrow(
            """
            INSERT INTO tenant_data.stock_transactions (
                tenant_id, product_id, transaction_type, quantity, reference_type, notes, reason_code
            ) VALUES ($1, $2, 'out', $3, 'manual', $4, $5)
            RETURNING *
            """,
            ctx.tenant_id,
            product["id"],
            body.qty,
            body.notes,
            body.reason_code or body.type,
        )
        await conn.execute(
            "UPDATE tenant_data.products SET stock_quantity = stock_quantity - $1 WHERE id = $2",
            body.qty,
            product["id"],
        )
        return {"id": tx["id"], "type": body.type, "status": "recorded"}

@router.post("/transfer", status_code=201)
async def create_stock_transfer(ctx: TenantCtxDep, body: StockTransferRequest, _auth: StaffDep):
    """
    Records a stock transfer between branches and returns Mushak 6.5 info.
    """
    async with ctx.transaction() as conn:
        product = await conn.fetchrow(
            "SELECT id, stock_quantity FROM tenant_data.products WHERE sku = $1 AND is_active = true FOR UPDATE",
            body.sku.strip(),
        )
        if not product:
            raise HTTPException(status_code=404, detail="Product SKU not found")
        if Decimal(str(product["stock_quantity"])) < body.qty:
            raise HTTPException(status_code=409, detail="Insufficient stock for this transfer")

        tx = await conn.fetchrow(
            """
            INSERT INTO tenant_data.stock_transactions (
                tenant_id, product_id, transaction_type, quantity, reference_type, notes, reason_code
            ) VALUES ($1, $2, 'out', $3, 'transfer', $4, 'branch_transfer')
            RETURNING *
            """,
            ctx.tenant_id,
            product["id"],
            body.qty,
            f"Transfer from {body.from_location} to {body.to_location}",
        )
        await conn.execute(
            "UPDATE tenant_data.products SET stock_quantity = stock_quantity - $1 WHERE id = $2",
            body.qty,
            product["id"],
        )
        return {"id": tx["id"], "mushak_form": "6.5", "status": "recorded"}

@router.get("/transfer/{tx_id}/mushak-6-5", responses={200: {"content": {"application/pdf": {}}}})
async def get_mushak_6_5_pdf(ctx: TenantCtxDep, tx_id: UUID, _auth: StaffDep):
    async with ctx.transaction() as conn:
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
            
        settings = await conn.fetchrow("SELECT * FROM platform.tenant_settings WHERE tenant_id = $1", ctx.tenant_id)

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
    c.drawString(1*inch, height - 2.2*inch, f"Registered Name: {settings['legal_title_en'] if settings else ctx.subdomain}")

    # Transfer Details
    c.rect(1*inch, height - 4*inch, width - 2*inch, 1.5*inch)
    c.drawString(1.2*inch, height - 2.8*inch, f"Product SKU: {tx['sku']}")
    c.drawString(1.2*inch, height - 3.0*inch, f"Description: {tx['name_en']}")
    c.drawString(1.2*inch, height - 3.2*inch, f"Quantity: {abs(tx['quantity'])} {tx['unit']}")
    c.drawString(1.2*inch, height - 3.4*inch, f"Movement: {str(tx['notes'])[:70]}")

    c.drawString(1*inch, height - 4.5*inch, "Signature of Issuing Officer:")
    c.line(1*inch, height - 5*inch, 3*inch, height - 5*inch)
    
    c.showPage()
    c.save()
    
    return Response(content=buf.getvalue(), media_type="application/pdf")

@router.get("/history", status_code=200)
async def get_inventory_history(ctx: TenantCtxDep, _auth: StaffDep):
    """
    Returns full history of stock transactions for auditing.
    """
    async with ctx.transaction() as conn:
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
