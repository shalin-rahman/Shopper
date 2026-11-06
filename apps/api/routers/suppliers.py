from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException
from schemas import PurchaseReturnCreate, DebitNoteOut
from core.tenant_context import TenantCtxDep
from core.dependencies import BranchDep, StaffDep
from services.stock import lock_products, record_movement, return_items

router = APIRouter(prefix="/v1/tenant/suppliers", tags=["procurement"])

@router.get("")
async def list_suppliers(ctx: TenantCtxDep, _auth: StaffDep):
    from core.config import get_settings
    settings = get_settings()

    if ctx.dedicated_db is None and settings.testing:
        from utils.seed_loader import suppliers as seed_suppliers
        return {"items": seed_suppliers(ctx.subdomain or "demo")}

    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT * FROM tenant_data.suppliers ORDER BY name_en")
    return {"items": [dict(r) for r in rows]}

@router.post("", status_code=201)
async def create_supplier(ctx: TenantCtxDep, body: dict, _auth: StaffDep):
    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.suppliers (tenant_id, code, name_en, name_bn, phone, email, address)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, code, name_en
            """,
            ctx.tenant_id, body.get("code"), body.get("name_en"), body.get("name_bn"),
            body.get("phone"), body.get("email"), body.get("address")
        )
    return dict(row)


@router.post("/returns", response_model=DebitNoteOut, status_code=201)
async def create_purchase_return(ctx: TenantCtxDep, body: PurchaseReturnCreate, _auth: StaffDep, branch: BranchDep):
    """
    Creates a Purchase Return (Mushak 6.8) and generates a Debit Note.
    Decreases the stock and potentially adjusts the general ledger.
    """
    async with ctx.transaction() as conn:
        # 1. Fetch original PO. The lock keeps two returns from both lowering its balance at once.
        po = await conn.fetchrow(
            "SELECT * FROM tenant_data.purchase_orders WHERE id = $1 FOR UPDATE", body.po_id
        )
        if not po:
            raise HTTPException(status_code=404, detail="Purchase Order not found")
        # Stock from a PO only arrives on receive, so there is nothing to send back before that.
        if po["status"] != "received":
            raise HTTPException(status_code=400, detail="Only a received purchase order can have a return")

        # 2. Calculate adjustment. Each item is priced at what the PO paid for it, and no
        # product can go back in larger numbers than the PO brought in, less earlier returns.
        items = return_items(body.items)
        on_po: dict[UUID, tuple[Decimal, Decimal]] = {}
        for line in await conn.fetch(
            "SELECT product_id, qty, unit_cost FROM tenant_data.po_lines WHERE po_id = $1", body.po_id
        ):
            qty_so_far, cost_so_far = on_po.get(line["product_id"], (Decimal("0"), Decimal("0")))
            line_qty = Decimal(str(line["qty"]))
            on_po[line["product_id"]] = (
                qty_so_far + line_qty,
                cost_so_far + line_qty * Decimal(str(line["unit_cost"])),
            )
        returned = {
            row["product_id"]: Decimal(str(row["qty"]))
            for row in await conn.fetch(
                """
                SELECT st.product_id, SUM(st.quantity) AS qty
                FROM tenant_data.stock_transactions st
                JOIN tenant_data.debit_notes d ON d.id = st.reference_id
                WHERE st.reference_type = 'purchase_return' AND d.po_id = $1
                GROUP BY st.product_id
                """,
                body.po_id,
            )
        }
        for product_id, qty in items:
            if product_id not in on_po:
                raise HTTPException(status_code=400, detail=f"Product {product_id} is not on this purchase order")
            if qty > on_po[product_id][0] - returned.get(product_id, Decimal("0")):
                raise HTTPException(
                    status_code=400,
                    detail=f"Return of product {product_id} is more than the purchase order has left to return",
                )

        await lock_products(conn, [product_id for product_id, _ in items])
        total_taxable = Decimal("0")
        total_vat = Decimal("0")
        for product_id, qty in items:
            line_qty, line_cost = on_po[product_id]
            cost = qty * line_cost / line_qty
            prod = await conn.fetchrow("SELECT vat_rate_pct FROM tenant_data.products WHERE id = $1", product_id)
            # The debit note carries VAT (Mushak 6.8); the PO total does not.
            vat = cost * Decimal(str(prod["vat_rate_pct"])) / Decimal("100") if prod else Decimal("0")
            total_taxable += cost
            total_vat += vat

        total_adjustment = total_taxable + total_vat
        # note_no is unique per tenant, so it comes from the note's own id, not the PO's.
        note_id = uuid4()
        note_no = f"DN-{datetime.now().strftime('%Y%m%d')}-{note_id.hex[:8].upper()}"

        # 3. Insert Debit Note (Mushak 6.8)
        dn_row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.debit_notes (
                id, tenant_id, note_no, reason, reference_id, po_id, supplier_id,
                adjustment_amount_taxable, adjustment_amount_vat, total_adjustment
            ) VALUES ($1, $2, $3, $4, $5, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            note_id, ctx.tenant_id, note_no, body.reason, body.po_id, po["supplier_id"],
            total_taxable, total_vat, total_adjustment
        )

        await conn.execute(
            """
            UPDATE tenant_data.purchase_orders
            SET total_amount = GREATEST(total_amount - $1, 0),
                balance_due = GREATEST(balance_due - $1, 0),
                updated_at = now()
            WHERE id = $2
            """,
            total_taxable, body.po_id
        )

        # 4. Update Stock (Record stock leaving the warehouse)
        branch_id = await branch.resolve(conn)
        for product_id, qty in items:
            await record_movement(
                conn, ctx, branch_id, product_id, "out", qty, "purchase_return", dn_row["id"],
                f"Purchase Return: {note_no}",
            )

    return DebitNoteOut(**dict(dn_row))
