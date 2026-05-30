from datetime import datetime
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from schemas import PurchaseReturnCreate, DebitNoteOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from deps import StaffDep

router = APIRouter(prefix="/v1/tenant/suppliers", tags=["procurement"])

@router.get("")
async def list_suppliers(request: Request, _auth: StaffDep):
    from config import get_settings
    from datetime import datetime
    settings = get_settings()
    pool = request.app.state.db_pool

    if pool is None and settings.testing:
        return {"items": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "name_en": "Mock Electronics Distro",
                "name_bn": "মক ইলেকট্রনিক্স ডিস্ট্রো",
                "phone": "01900000000",
                "is_active": True
            }
        ]}

    sub = subdomain_from_request(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch("SELECT * FROM tenant_data.suppliers ORDER BY name_en")
    return {"items": [dict(r) for r in rows]}

@router.post("", status_code=201)
async def create_supplier(request: Request, body: dict, _auth: StaffDep):
    sub = subdomain_from_request(request)
    pool = request.app.state.db_pool
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.suppliers (tenant_id, code, name_en, name_bn, phone, email, address)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, code, name_en
            """,
            tenant_id, body.get("code"), body.get("name_en"), body.get("name_bn"),
            body.get("phone"), body.get("email"), body.get("address")
        )
    return dict(row)


@router.post("/returns", response_model=DebitNoteOut, status_code=201)
async def create_purchase_return(request: Request, body: PurchaseReturnCreate, _auth: StaffDep):
    """
    Creates a Purchase Return (Mushak 6.8) and generates a Debit Note.
    Decreases the stock and potentially adjusts the general ledger.
    """
    sub = subdomain_from_request(request)
    pool = request.app.state.db_pool
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        # 1. Fetch original PO
        po = await conn.fetchrow(
            "SELECT * FROM tenant_data.purchase_orders WHERE id = $1", body.po_id
        )
        if not po:
            raise HTTPException(status_code=404, detail="Purchase Order not found")

        # 2. Calculate adjustment
        total_taxable = Decimal("0")
        total_vat = Decimal("0")
        for item in body.items:
            # Fetch product info for unit cost
            prod = await conn.fetchrow("SELECT buy_price, vat_rate_pct FROM tenant_data.products WHERE id = $1", item["product_id"])
            if prod:
                cost = Decimal(str(item["qty"])) * Decimal(str(prod["buy_price"]))
                # Include VAT in adjustment if applicable ( Mushak 6.8 logic)
                vat = (cost * Decimal(str(prod["vat_rate_pct"]))) / Decimal("100")
                total_taxable += cost
                total_vat += vat

        total_adjustment = total_taxable + total_vat
        note_no = f"DN-{datetime.now().strftime('%Y%m%d')}-{body.po_id.hex[:4]}"

        # 3. Insert Debit Note (Mushak 6.8)
        dn_row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.debit_notes (
                tenant_id, reference_id, note_no, reason, 
                adjustment_amount_taxable, adjustment_amount_vat, total_adjustment
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            tenant_id, body.po_id, note_no, body.reason,
            total_taxable, total_vat, total_adjustment
        )

        # 4. Update Stock (Record stock leaving the warehouse)
        for item in body.items:
             await conn.execute(
                """
                INSERT INTO tenant_data.stock_transactions (
                    tenant_id, product_id, transaction_type, quantity, 
                    reference_type, reference_id, notes
                ) VALUES ($1, $2, 'out', $3, 'purchase_return', $4, $5)
                """,
                tenant_id, item["product_id"], -item["qty"], 
                dn_row["id"], f"Purchase Return: {note_no}"
            )
             
             await conn.execute(
                 "UPDATE tenant_data.products SET stock_quantity = stock_quantity - $1 WHERE id = $2",
                 item["qty"], item["product_id"]
             )

    return DebitNoteOut(**dict(dn_row))
