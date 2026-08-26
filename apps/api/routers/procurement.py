from __future__ import annotations
from decimal import Decimal
from uuid import UUID
from datetime import datetime
import asyncpg
from fastapi import APIRouter, HTTPException, Query
from core.dependencies import StaffDep
from schemas import (
    POCreate, POOut, POLineOut, 
    SupplierPaymentCreate, SupplierPaymentOut,
    PurchaseReturnCreate, DebitNoteOut
)
from core.tenant_context import TenantCtxDep

router = APIRouter(prefix="/v1/tenant/procurement", tags=["procurement"])

@router.post("/po", response_model=POOut, status_code=201)
async def create_purchase_order(ctx: TenantCtxDep, body: POCreate, _auth: StaffDep):
    total_amount = sum(line.qty * line.unit_cost for line in body.lines)

    async with ctx.transaction() as conn:
        # Create PO
        po_row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.purchase_orders (
                tenant_id, supplier_id, po_no, total_amount, balance_due, status
            ) VALUES ($1, $2, $3, $4, $4, 'draft')
            RETURNING *
            """,
            ctx.tenant_id, body.supplier_id, body.po_no, total_amount
        )
        
        po_id = po_row["id"]
        line_rows = []
        for line in body.lines:
            lr = await conn.fetchrow(
                """
                INSERT INTO tenant_data.po_lines (po_id, product_id, qty, unit_cost, line_total)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                po_id, line.product_id, line.qty, line.unit_cost, line.qty * line.unit_cost
            )
            line_rows.append(lr)

    return _po_row_to_out(po_row, line_rows)

@router.post("/po/{po_id}/receive", status_code=200)
async def receive_po(ctx: TenantCtxDep, po_id: UUID, _auth: StaffDep):
    """
    Finalizes a PO and increases stock for all items.
    """
    async with ctx.transaction() as conn:
        po = await conn.fetchrow("SELECT status FROM tenant_data.purchase_orders WHERE id = $1", po_id)
        if not po: raise HTTPException(status_code=404, detail="PO not found")
        if po["status"] == "received": raise HTTPException(status_code=400, detail="PO already received")

        lines = await conn.fetch("SELECT * FROM tenant_data.po_lines WHERE po_id = $1", po_id)
        
        for line in lines:
            # 1. Update Product Stock and WAC cost (simplified)
            await conn.execute(
                """
                UPDATE tenant_data.products 
                SET stock_quantity = stock_quantity + $1,
                    buy_price = $2,
                    updated_at = now()
                WHERE id = $3
                """,
                line["qty"], line["unit_cost"], line["product_id"]
            )
            
            # 2. Record Stock transaction
            await conn.execute(
                """
                INSERT INTO tenant_data.stock_transactions (
                    tenant_id, product_id, transaction_type, quantity, unit_cost, reference_type, reference_id, notes
                ) VALUES ($1, $2, 'in', $3, $4, 'po', $5, $6)
                """,
                ctx.tenant_id, line["product_id"], line["qty"], line["unit_cost"], po_id, f"Received PO: {po_id}"
            )

        await conn.execute("UPDATE tenant_data.purchase_orders SET status = 'received', updated_at = now() WHERE id = $1", po_id)

    return {"status": "success", "message": "Inventory updated"}

@router.post("/payments", response_model=SupplierPaymentOut, status_code=201)
async def record_supplier_payment(ctx: TenantCtxDep, body: SupplierPaymentCreate, _auth: StaffDep):
    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.supplier_payments (
                tenant_id, supplier_id, po_id, payment_no, amount, payment_method, ref_no
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            ctx.tenant_id, body.supplier_id, body.po_id, body.payment_no, body.amount, body.payment_method, body.ref_no
        )

        if body.po_id:
            await conn.execute(
                """
                UPDATE tenant_data.purchase_orders 
                SET amount_paid = amount_paid + $1, 
                    balance_due = balance_due - $1,
                    updated_at = now()
                WHERE id = $2
                """,
                body.amount, body.po_id
            )

    return SupplierPaymentOut(**dict(row))

@router.post("/returns", response_model=DebitNoteOut, status_code=201)
async def create_purchase_return(ctx: TenantCtxDep, body: PurchaseReturnCreate, _auth: StaffDep):
    """
    Mushak 6.8 - Debit Note. Returning goods to supplier.
    """
    async with ctx.transaction() as conn:
        po = await conn.fetchrow("SELECT supplier_id FROM tenant_data.purchase_orders WHERE id = $1", body.po_id)
        if not po: raise HTTPException(status_code=404, detail="PO not found")

        total_adj = Decimal("0")
        for item in body.items:
            # Reverse stock
            await conn.execute(
                "UPDATE tenant_data.products SET stock_quantity = stock_quantity - $1 WHERE id = $2",
                item["qty"], item["product_id"]
            )
            # Fetch cost
            cost = await conn.fetchval("SELECT buy_price FROM tenant_data.products WHERE id = $1", item["product_id"])
            total_adj += Decimal(str(item["qty"])) * Decimal(str(cost or 0))

        note_no = f"DN-{datetime.now().strftime('%Y%m%d')}-{body.po_id.hex[:4]}"
        
        dn_row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.debit_notes (
                tenant_id, supplier_id, po_id, note_no, reason, total_adjustment
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            ctx.tenant_id, po["supplier_id"], body.po_id, note_no, body.reason, total_adj
        )

        # Reduce PO balance
        await conn.execute(
            "UPDATE tenant_data.purchase_orders SET total_amount = total_amount - $1, balance_due = balance_due - $1 WHERE id = $2",
            total_adj, body.po_id
        )

    return DebitNoteOut(
        id=dn_row["id"],
        note_no=dn_row["note_no"],
        reference_id=dn_row["po_id"],
        reason=dn_row["reason"],
        total_adjustment=dn_row["total_adjustment"],
        created_at=dn_row["created_at"]
    )

@router.get("/po", response_model=list[POOut])
async def list_purchase_orders(ctx: TenantCtxDep, _auth: StaffDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT * FROM tenant_data.purchase_orders ORDER BY created_at DESC")
        results = []
        for r in rows:
            lines = await conn.fetch("SELECT * FROM tenant_data.po_lines WHERE po_id = $1", r["id"])
            results.append(_po_row_to_out(r, lines))
        return results

@router.get("/payments", response_model=list[SupplierPaymentOut])
async def list_supplier_payments(ctx: TenantCtxDep, _auth: StaffDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT * FROM tenant_data.supplier_payments ORDER BY created_at DESC")
        return [SupplierPaymentOut(**dict(r)) for r in rows]

@router.get("/returns", response_model=list[DebitNoteOut])
async def list_purchase_returns(ctx: TenantCtxDep, _auth: StaffDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT * FROM tenant_data.debit_notes ORDER BY created_at DESC")
        return [
            DebitNoteOut(
                id=r["id"],
                note_no=r["note_no"],
                reference_id=r["po_id"],
                reason=r["reason"],
                total_adjustment=r["total_adjustment"],
                created_at=r["created_at"]
            ) for r in rows
        ]

def _po_row_to_out(row: asyncpg.Record, lines: list[asyncpg.Record]) -> POOut:
    d = dict(row)
    for k in ("total_amount", "amount_paid", "balance_due"):
        if d.get(k) is not None: d[k] = Decimal(str(d[k]))
    
    out_lines = []
    for lr in lines:
        ld = dict(lr)
        ld["qty"] = Decimal(str(ld["qty"]))
        ld["unit_cost"] = Decimal(str(ld["unit_cost"]))
        ld["line_total"] = Decimal(str(ld["line_total"]))
        out_lines.append(POLineOut(**ld))
    
    d["lines"] = out_lines
    return POOut(**d)
