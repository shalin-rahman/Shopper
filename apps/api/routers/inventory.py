from __future__ import annotations
from decimal import Decimal
from typing import Literal
from uuid import UUID
import io
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, model_validator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

from core.tenant_context import TenantCtxDep
from core.dependencies import BranchChoice, BranchDep, StaffDep, limited_staff_uid
from services.stock import lock_levels, record_movement

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
    # Send exactly one of these.
    product_id: UUID | None = None
    sku: str | None = None
    qty: Decimal = Field(..., gt=0)
    to_branch_id: UUID
    # None means the main branch.
    from_branch_id: UUID | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _one_product_key(self):
        if self.sku is not None:
            self.sku = self.sku.strip() or None
        if (self.product_id is None) == (self.sku is None):
            raise ValueError("Send exactly one of product_id or sku")
        return self


@router.post("/receive", status_code=201)
async def stock_receive(ctx: TenantCtxDep, body: StockReceiveRequest, _auth: StaffDep, branch: BranchDep):
    """
    Increases stock. Reasons: purchase, gift_in, return_in.
    """
    async with ctx.transaction() as conn:
        # The one product row, locked before any stock row, as lock_products does.
        product = await conn.fetchrow(
            "SELECT id FROM tenant_data.products WHERE sku = $1 AND is_active = true FOR UPDATE",
            body.sku.strip(),
        )
        if not product:
            raise HTTPException(status_code=404, detail="Product SKU not found")

        tx = await record_movement(
            conn, ctx, await branch.resolve(conn), product["id"], "in", body.qty,
            "manual", None, body.notes,
            unit_cost=body.unit_cost, reason_code=body.reason_code or body.type,
        )
        return {"id": tx["id"], "type": body.type, "status": "recorded"}

@router.post("/adjust", status_code=201)
async def stock_adjust(ctx: TenantCtxDep, body: StockAdjustRequest, _auth: StaffDep, branch: BranchDep):
    """
    Decreases stock. Reasons: damage, return_out, gift_out, expired.
    """
    async with ctx.transaction() as conn:
        # The one product row, locked before any stock row, as lock_products does.
        product = await conn.fetchrow(
            "SELECT id FROM tenant_data.products WHERE sku = $1 AND is_active = true FOR UPDATE",
            body.sku.strip(),
        )
        if not product:
            raise HTTPException(status_code=404, detail="Product SKU not found")

        # Raises 409 if the branch holds less than qty.
        tx = await record_movement(
            conn, ctx, await branch.resolve(conn), product["id"], "out", body.qty,
            "manual", None, body.notes, reason_code=body.reason_code or body.type,
        )
        return {"id": tx["id"], "type": body.type, "status": "recorded"}

@router.post("/transfer", status_code=201)
async def create_stock_transfer(ctx: TenantCtxDep, body: StockTransferRequest, auth: StaffDep):
    """
    Moves stock from one branch to another and returns Mushak 6.5 info.
    The returned id is the transfer_out row, which the 6.5 PDF prints.
    """
    async with ctx.transaction() as conn:
        # The one product row, locked before any stock row, as lock_products does.
        product = await conn.fetchrow(
            """
            SELECT id FROM tenant_data.products
            WHERE ($1::uuid IS NULL OR id = $1) AND ($2::text IS NULL OR sku = $2) AND is_active = true
            FOR UPDATE
            """,
            body.product_id,
            body.sku,
        )
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Cashiers and accountants may only send from their own branch.
        from_id = await BranchChoice(body.from_branch_id, limited_staff_uid(auth)).resolve(conn)
        to_id = await BranchChoice(body.to_branch_id).resolve(conn)
        if from_id == to_id:
            raise HTTPException(status_code=400, detail="Source and destination branch are the same")

        # Lock both branches' rows in branch order so two opposite transfers cannot deadlock.
        levels = {}
        for branch_id in sorted([from_id, to_id]):
            levels[branch_id] = await lock_levels(conn, branch_id, [product["id"]])
        if levels[from_id][product["id"]] < body.qty:
            raise HTTPException(status_code=409, detail="Insufficient stock at the source branch")

        notes = body.notes or "Branch transfer"
        sent = await record_movement(
            conn, ctx, from_id, product["id"], "transfer_out", body.qty,
            "transfer", None, notes, reason_code="branch_transfer",
        )
        await record_movement(
            conn, ctx, to_id, product["id"], "transfer_in", body.qty,
            "transfer", sent["id"], notes, reason_code="branch_transfer",
        )
        return {"id": sent["id"], "mushak_form": "6.5", "status": "recorded"}

@router.get("/transfer/{tx_id}/mushak-6-5", responses={200: {"content": {"application/pdf": {}}}})
async def get_mushak_6_5_pdf(ctx: TenantCtxDep, tx_id: UUID, _auth: StaffDep):
    async with ctx.transaction() as conn:
        tx = await conn.fetchrow(
            """
            SELECT tx.*, p.name_en, p.sku, p.unit,
                   fb.name AS from_branch, tb.name AS to_branch
            FROM tenant_data.stock_transactions tx
            JOIN tenant_data.products p ON tx.product_id = p.id
            LEFT JOIN tenant_data.branches fb ON fb.id = tx.branch_id
            LEFT JOIN tenant_data.stock_transactions rx
                ON rx.reference_type = 'transfer' AND rx.reference_id = tx.id
               AND rx.transaction_type = 'transfer_in'
            LEFT JOIN tenant_data.branches tb ON tb.id = rx.branch_id
            WHERE tx.id = $1
              AND tx.reference_type = 'transfer' AND tx.transaction_type IN ('transfer_out', 'out')
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
    # Transfers made before per-branch stock have no transfer_in row; their notes name the places.
    movement = f"{tx['from_branch']} -> {tx['to_branch']}" if tx["to_branch"] else str(tx["notes"])
    c.drawString(1.2*inch, height - 3.4*inch, f"Movement: {movement[:70]}")

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
