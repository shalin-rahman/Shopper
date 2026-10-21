from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg
import asyncpg.exceptions
from fastapi import APIRouter, HTTPException, Response
from reportlab.graphics.barcode import code128
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from core.dependencies import SettingsDep, StaffDep
from core.tenant_context import TenantCtxDep
from schemas import ProductCreate, ProductOut, ProductUpdate
from utils.codes import barcode_for_sku, qr_payload_for_product

router = APIRouter(prefix="/v1/tenant/products", tags=["products"])

@router.get("", response_model=list[ProductOut])
async def list_products(ctx: TenantCtxDep, _auth: StaffDep, settings: SettingsDep):
    if ctx.dedicated_db is None and settings.testing:
        from utils.seed_loader import products as seed_products
        return [
            ProductOut(**{k: Decimal(v) if k in ("buy_price", "sell_price", "mrp", "vat_rate_pct", "stock_quantity") and v else v for k, v in p.items()})
            for p in seed_products(ctx.subdomain or "demo")
        ]

    async with ctx.transaction() as conn:
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, category_id, sku, name_en, name_bn,
                   description_en, description_bn, unit,
                   buy_price, sell_price, mrp, vat_rate_pct,
                   barcode, qr_payload, stock_quantity, is_active, marketplace_enabled, created_at, updated_at
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
                   barcode, qr_payload, stock_quantity, is_active, marketplace_enabled, created_at, updated_at
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
    bc = barcode_for_sku(body.sku)
    qr = qr_payload_for_product(settings.storefront_public_base_url or "", ctx.subdomain, body.sku)

    async with ctx.transaction() as conn:
        try:
            if body.category_id is not None:
                category_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM tenant_data.product_categories WHERE id = $1)",
                    body.category_id,
                )
                if not category_exists:
                    raise HTTPException(status_code=422, detail="Category does not exist for this tenant")

            row = await conn.fetchrow(
                """
                INSERT INTO tenant_data.products (
                    tenant_id, category_id, sku, name_en, name_bn,
                    description_en, description_bn, unit,
                    buy_price, sell_price, mrp, vat_rate_pct,
                    barcode, qr_payload, stock_quantity, is_active, marketplace_enabled
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, true, $16)
                RETURNING id, tenant_id, category_id, sku, name_en, name_bn,
                          description_en, description_bn, unit,
                          buy_price, sell_price, mrp, vat_rate_pct,
                          barcode, qr_payload, stock_quantity, is_active, marketplace_enabled, created_at, updated_at
                """,
                ctx.tenant_id,
                body.category_id,
                body.sku.strip(),
                body.name_en.strip(),
                body.name_bn.strip(),
                body.description_en,
                body.description_bn,
                body.unit.strip(),
                body.buy_price,
                body.sell_price,
                body.mrp,
                body.vat_rate_pct,
                bc,
                qr,
                body.stock_quantity,
                body.marketplace_enabled,
            )

            if body.stock_quantity > 0:
                await conn.execute(
                    """
                    INSERT INTO tenant_data.stock_transactions (
                        tenant_id, product_id, transaction_type, quantity, unit_cost, reference_type, notes
                    ) VALUES ($1, $2, 'in', $3, $4, 'manual', 'Initial stock')
                    """,
                    ctx.tenant_id,
                    row["id"],
                    body.stock_quantity,
                    body.buy_price,
                )
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=409, detail="SKU already exists")
    return _row_to_out(row)

@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(ctx: TenantCtxDep, product_id: UUID, body: ProductUpdate, _auth: StaffDep):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return await get_product(ctx, product_id, _auth)

    async with ctx.transaction() as conn:
        category_id = fields.get("category_id")
        if category_id is not None:
            category_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM tenant_data.product_categories WHERE id = $1)",
                category_id,
            )
            if not category_exists:
                raise HTTPException(status_code=422, detail="Category does not exist for this tenant")

        old = await conn.fetchrow(
            "SELECT stock_quantity, buy_price FROM tenant_data.products WHERE id = $1 FOR UPDATE",
            product_id,
        )
        if not old:
            raise HTTPException(status_code=404, detail="Product not found")

        set_parts = [f"{key} = ${index + 1}" for index, key in enumerate(fields.keys())]
        set_parts.append("updated_at = now()")
        args = list(fields.values())
        args.append(product_id)

        row = await conn.fetchrow(
            f"UPDATE tenant_data.products SET {', '.join(set_parts)} WHERE id = ${len(args)} "
            "RETURNING id, tenant_id, category_id, sku, name_en, name_bn, description_en, description_bn, "
            "unit, buy_price, sell_price, mrp, vat_rate_pct, barcode, qr_payload, stock_quantity, is_active, marketplace_enabled, created_at, updated_at",
            *args,
        )

        if "stock_quantity" in fields:
            old_qty = Decimal(str(old["stock_quantity"]))
            new_qty = Decimal(str(fields["stock_quantity"]))
            diff = new_qty - old_qty
            if diff != 0:
                unit_cost = fields.get("buy_price", old["buy_price"])
                await conn.execute(
                    """
                    INSERT INTO tenant_data.stock_transactions (
                        tenant_id, product_id, transaction_type, quantity, unit_cost, reference_type, notes
                    ) VALUES ($1, $2, $3, $4, $5, 'manual', 'Stock adjustment')
                    """,
                    ctx.tenant_id,
                    product_id,
                    "in" if diff > 0 else "out",
                    abs(diff),
                    unit_cost,
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
    """Generate a printable PDF product label."""
    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT sku, name_en, sell_price, barcode FROM tenant_data.products WHERE id = $1",
            product_id,
        )
        tenant_settings = await conn.fetchrow(
            "SELECT legal_title_en FROM platform.tenant_settings WHERE tenant_id = $1",
            ctx.tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    tenant_name = tenant_settings["legal_title_en"] if tenant_settings and tenant_settings["legal_title_en"] else ctx.subdomain or "Shopper"
    buf = __import__("io").BytesIO()
    c = canvas.Canvas(buf, pagesize=(2 * inch, 1 * inch))

    prod_name = str(row["name_en"])[:25]
    price = f"BDT {row['sell_price']}" if row["sell_price"] else ""
    barcode_val = row["barcode"] or row["sku"]

    c.setFont("Helvetica-Bold", 6)
    c.drawString(0.05 * inch, 0.85 * inch, tenant_name[:20])
    c.setFont("Helvetica", 6)
    c.drawString(0.05 * inch, 0.75 * inch, prod_name)

    barcode = code128.Code128(barcode_val, barHeight=0.4 * inch, barWidth=0.012 * inch)
    barcode.drawOn(c, 0.1 * inch, 0.25 * inch)

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
