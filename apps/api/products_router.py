from __future__ import annotations
from decimal import Decimal
from uuid import UUID
import asyncpg
import asyncpg.exceptions
from fastapi import APIRouter, HTTPException, Request
from codes import barcode_for_sku, qr_payload_for_product
from deps import SettingsDep, StaffDep
from schemas import ProductCreate, ProductOut, ProductUpdate
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction

router = APIRouter(prefix="/v1/tenant/products", tags=["products"])

def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool

@router.get("", response_model=list[ProductOut])
async def list_products(request: Request, _auth: StaffDep):
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
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
async def get_product(request: Request, product_id: UUID, _auth: StaffDep):
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
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
async def create_product(request: Request, body: ProductCreate, settings: SettingsDep, _auth: StaffDep):
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    bc = barcode_for_sku(body.sku)
    qr = qr_payload_for_product(settings.storefront_public_base_url or "", sub, body.sku)

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
async def update_product(request: Request, product_id: UUID, body: ProductUpdate, _auth: StaffDep):
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
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
async def delete_product(request: Request, product_id: UUID, _auth: StaffDep):
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        res = await conn.execute("UPDATE tenant_data.products SET is_active = false, updated_at = now() WHERE id = $1", product_id)
    if res == "UPDATE 0": raise HTTPException(status_code=404, detail="Product not found")
    return None

def _row_to_out(row: asyncpg.Record) -> ProductOut:
    d = dict(row)
    for k in ("buy_price", "sell_price", "mrp", "vat_rate_pct", "stock_quantity"):
        if d.get(k) is not None: d[k] = Decimal(str(d[k]))
    return ProductOut(**d)
