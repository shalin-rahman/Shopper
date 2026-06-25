from __future__ import annotations
from decimal import Decimal
from uuid import UUID
import asyncpg
import asyncpg.exceptions
from fastapi import APIRouter, HTTPException, Request
from utils.codes import barcode_for_sku, qr_payload_for_product
from core.dependencies import SettingsDep, StaffDep
from schemas import ProductCreate, ProductOut, ProductUpdate
from core.tenant_context import TenantCtxDep

router = APIRouter(prefix="/v1/tenant/products", tags=["products"])

def _pool(ctx: TenantCtxDep) -> asyncpg.Pool:
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool

@router.get("", response_model=list[ProductOut])
async def list_products(ctx: TenantCtxDep, _auth: StaffDep, settings: SettingsDep):
    
    if ctx.dedicated_db is None and settings.testing:  # mocked
        # Mock data for UI demonstration
        from datetime import datetime
        return [
            ProductOut(
                id=UUID("00000000-0000-0000-0000-000000000001"),
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                category_id=None,
                sku="MOCK-001",
                name_en="Sample Smartphone",
                name_bn="স্মার্টফোন নমুনা",
                description_en="High end smartphone",
                description_bn="উচ্চ মানের স্মার্টফোন",
                buy_price=Decimal("15000.00"),
                sell_price=Decimal("18500.00"),
                mrp=Decimal("19000.00"),
                vat_rate_pct=Decimal("5.0"),
                stock_quantity=Decimal("50"),
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                unit="pcs",
                barcode="12345678",
                qr_payload="https://shopper.com/p/MOCK-001"
            ),
            ProductOut(
                id=UUID("00000000-0000-0000-0000-000000000002"),
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                category_id=None,
                sku="MOCK-002",
                name_en="Wireless Keyboard",
                name_bn="ওয়্যারলেস কিবোর্ড",
                description_en="Bluetooth keyboard",
                description_bn="ব্লুটুথ কীবোর্ড",
                buy_price=Decimal("2000.00"),
                sell_price=Decimal("2500.00"),
                mrp=Decimal("2800.00"),
                vat_rate_pct=Decimal("5.0"),
                stock_quantity=Decimal("120"),
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                unit="pcs",
                barcode="87654321",
                qr_payload="https://shopper.com/p/MOCK-002"
            )
        ]

    async with ctx.transaction() as conn:
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, category_id, sku, name_en, name_bn,
                   description_en, description_bn, unit,
                   buy_price, sell_price, mrp, vat_rate_pct,
                   barcode, qr_payload, stock_quantity, is_active, created_at, updated_at
            FROM tenant_data.products
            ORDER BY sku
            """
        )
    return [_row_to_out(r) for r in rows]

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(ctx: TenantCtxDep, product_id: UUID, _auth: StaffDep):
    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, tenant_id, category_id, sku, name_en, name_bn,
                   description_en, description_bn, unit,
                   buy_price, sell_price, mrp, vat_rate_pct,
                   barcode, qr_payload, stock_quantity, is_active, created_at, updated_at
            FROM tenant_data.products
            WHERE id = $1
            """,
            product_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return _row_to_out(row)

@router.post("", response_model=ProductOut, status_code=201)
async def create_product(ctx: TenantCtxDep, body: ProductCreate, settings: SettingsDep, _auth: StaffDep):
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, ctx.subdomain)
    ctx.tenant_id = tenant["id"]
    bc = barcode_for_sku(body.sku)
    qr = qr_payload_for_product(settings.storefront_public_base_url or "", ctx.subdomain, body.sku)

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO tenant_data.products (
                    tenant_id, category_id, sku, name_en, name_bn,
                    description_en, description_bn, unit,
                    buy_price, sell_price, mrp, vat_rate_pct,
                    barcode, qr_payload, stock_quantity, is_active
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, true)
                RETURNING id, tenant_id, category_id, sku, name_en, name_bn,
                          description_en, description_bn, unit,
                          buy_price, sell_price, mrp, vat_rate_pct,
                          barcode, qr_payload, stock_quantity, is_active, created_at, updated_at
                """,
                tenant_id, body.category_id, body.sku.strip(), body.name_en.strip(), body.name_bn.strip(),
                body.description_en, body.description_bn, body.unit.strip(),
                body.buy_price, body.sell_price, body.mrp, body.vat_rate_pct,
                bc, qr, body.stock_quantity
            )
            
            # Record initial stock transaction if stock > 0
            if body.stock_quantity > 0:
                await conn.execute(
                    """
                    INSERT INTO tenant_data.stock_transactions (
                        tenant_id, product_id, transaction_type, quantity, unit_cost, reference_type, notes
                    ) VALUES ($1, $2, 'in', $3, $4, 'manual', 'Initial stock')
                    """,
                    tenant_id, row["id"], body.stock_quantity, body.buy_price
                )
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=409, detail="SKU already exists")
    return _row_to_out(row)

@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(ctx: TenantCtxDep, product_id: UUID, body: ProductUpdate, _auth: StaffDep):
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, ctx.subdomain)
    ctx.tenant_id = tenant["id"]
    fields = body.model_dump(exclude_unset=True)
    if not fields: return await get_product(request, product_id, _auth)

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        old = await conn.fetchrow("SELECT stock_quantity, buy_price FROM tenant_data.products WHERE id = $1", product_id)
        if not old: raise HTTPException(status_code=404, detail="Product not found")

        set_parts = [f"{k} = ${i+1}" for i, k in enumerate(fields.keys())]
        set_parts.append("updated_at = now()")
        args = list(fields.values())
        args.append(product_id)
        
        row = await conn.fetchrow(
            f"UPDATE tenant_data.products SET {', '.join(set_parts)} WHERE id = ${len(args)} "
            "RETURNING id, tenant_id, category_id, sku, name_en, name_bn, description_en, description_bn, "
            "unit, buy_price, sell_price, mrp, vat_rate_pct, barcode, qr_payload, stock_quantity, is_active, created_at, updated_at",
            *args
        )

        # Log adjustment if stock_quantity was updated
        if "stock_quantity" in fields:
            diff = fields["stock_quantity"] - old["stock_quantity"]
            if diff != 0:
                await conn.execute(
                    """
                    INSERT INTO tenant_data.stock_transactions (
                        tenant_id, product_id, transaction_type, quantity, unit_cost, reference_type, notes
                    ) VALUES ($1, $2, $3, $4, $5, 'manual', 'Stock adjustment')
                    """,
                    tenant_id, product_id, 'in' if diff > 0 else 'out', abs(diff), fields.get("buy_price", old["buy_price"])
                )
    return _row_to_out(row)

@router.delete("/{product_id}", status_code=204)
async def delete_product(ctx: TenantCtxDep, product_id: UUID, _auth: StaffDep):
    async with ctx.transaction() as conn:
        res = await conn.execute("UPDATE tenant_data.products SET is_active = false, updated_at = now() WHERE id = $1", product_id)
    if res == "UPDATE 0": raise HTTPException(status_code=404, detail="Product not found")
    return None

@router.get("/{product_id}/label", responses={200: {"content": {"application/pdf": {}}}})
async def get_product_label(ctx: TenantCtxDep, product_id: UUID, _auth: StaffDep):
    """
    Generates a 2x1 inch thermal-printer ready PDF label with a 1D Code128 Barcode.
    """
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, ctx.subdomain)
    ctx.tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            "SELECT sku, name_en, sell_price, barcode FROM tenant_data.products WHERE id = $1",
            product_id
        )
        settings = await conn.fetchrow("SELECT legal_title_en FROM platform.tenant_settings WHERE ctx.tenant_id = $1", tenant_id)
        
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    import io
    from reportlab.pdfgen import canvas
    from reportlab.graphics.barcode import code128
    from reportlab.lib.units import inch
    from fastapi import Response

    buf = io.BytesIO()
    # 2 inches wide x 1 inch high
    c = canvas.Canvas(buf, pagesize=(2 * inch, 1 * inch))
    
    tenant_name = settings["legal_title_en"][:20] if settings and settings.get("legal_title_en") else ctx.subdomain
    prod_name = str(row["name_en"])[:25]
    price = f"BDT {row['sell_price']}" if row['sell_price'] else ""
    barcode_val = row["barcode"] or row["sku"]

    # Header / Meta
    c.setFont("Helvetica-Bold", 6)
    c.drawString(0.05 * inch, 0.85 * inch, tenant_name)
    c.setFont("Helvetica", 6)
    c.drawString(0.05 * inch, 0.75 * inch, prod_name)
    
    # Generate Code128 Barcode
    barcode = code128.Code128(barcode_val, barHeight=0.4*inch, barWidth=0.012*inch)
    # Center the barcode (approximate drawing offsets)
    barcode.drawOn(c, 0.1 * inch, 0.25 * inch)
    
    # Price
    c.setFont("Helvetica-Bold", 8)
    c.drawRightString(1.9 * inch, 0.1 * inch, price)

    c.showPage()
    c.save()

    return Response(content=buf.getvalue(), media_type="application/pdf")

def _row_to_out(row: asyncpg.Record) -> ProductOut:
    d = dict(row)
    for k in ("buy_price", "sell_price", "mrp", "vat_rate_pct", "stock_quantity"):
        if d.get(k) is not None: d[k] = Decimal(str(d[k]))
    return ProductOut(**d)
