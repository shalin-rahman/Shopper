from __future__ import annotations
from uuid import UUID
from typing import Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from deps import StaffDep

router = APIRouter(prefix="/v1/tenant/pos", tags=["pos"])

@router.get("/sync")
async def pos_sync_data(request: Request, _auth: StaffDep):
    """
    Returns a consolidated payload of products and categories for local mobile caching.
    """
    sub = subdomain_from_request(request)
    pool = request.app.state.db_pool
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        categories = await conn.fetch("SELECT id, name_en, name_bn FROM tenant_data.product_categories")
        products = await conn.fetch(
            """
            SELECT id, category_id, sku, name_en, name_bn, sell_price, vat_rate_pct, barcode, qr_payload, stock_quantity
            FROM tenant_data.products
            WHERE is_active = true
            """
        )

    return {
        "categories": [dict(c) for c in categories],
        "products": [dict(p) for p in products]
    }

@router.post("/offline-punch")
async def pos_offline_punch(request: Request, body: list[dict[str, Any]], _auth: StaffDep):
    """
    Processes a batch of offline-synced orders.
    Orchestrates Invoice -> Stock Transactions -> VAT Register population.
    """
    sub = subdomain_from_request(request)
    pool = request.app.state.db_pool
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    synced_ids = []

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        for order_data in body:
            try:
                # 1. Insert Invoice
                invoice_id = await conn.fetchval(
                    """
                    INSERT INTO tenant_data.invoices (
                        invoice_no, total_amount, subtotal, discount, total_vat, 
                        buyer_name_en, phone, status, amount_paid, balance_due, notes
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING id
                    """,
                    order_data.get("orderNumber"),
                    order_data.get("total"),
                    order_data.get("subtotal"),
                    order_data.get("discount", 0),
                    order_data.get("taxAmount", 0),
                    order_data.get("customerName"),
                    order_data.get("customerPhone"),
                    "paid",
                    order_data.get("total"),
                    0,
                    order_data.get("notes")
                )

                # 2. Process Items
                for item in order_data.get("items", []):
                    # Insert Invoice Line
                    await conn.execute(
                        """
                        INSERT INTO tenant_data.invoice_lines (
                            invoice_id, product_id, quantity, unit_price, vat_rate_pct, vat_amount, total_amount
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        invoice_id,
                        item.get("productId"),
                        item.get("quantity"),
                        item.get("unitPrice"),
                        item.get("vatRatePct", 0),
                        item.get("vatAmount", 0),
                        (item.get("unitPrice") * item.get("quantity")) + item.get("vatAmount", 0)
                    )

                    # 3. Stock Transaction (Triggers WAC/FIFO logic)
                    await conn.execute(
                        """
                        INSERT INTO tenant_data.stock_transactions (
                            tenant_id, product_id, transaction_type, quantity, reference_type, reference_id, notes
                        ) VALUES ($1, $2, 'out', $3, 'sale', $4, $5)
                        """,
                        tenant_id,
                        item.get("productId"),
                        item.get("quantity"),
                        invoice_id,
                        f"POS Sale: {order_data.get('orderNumber')}"
                    )

                    # 4. Manual Stock Update (since no trigger exists for products table)
                    await conn.execute(
                        "UPDATE tenant_data.products SET stock_quantity = stock_quantity - $1 WHERE id = $2",
                        item.get("quantity"),
                        item.get("productId")
                    )

                    # 5. VAT Sales Register (Mushak 6.3 entry)
                    await conn.execute(
                        """
                        INSERT INTO tenant_data.vat_sales_register_lines (
                            tenant_id, mushak_form, invoice_no, invoice_date, 
                            buyer_name_en, description_en, qty, taxable_value, vat_amount, total_amount
                        ) VALUES ($1, '6.3', $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        tenant_id,
                        order_data.get("orderNumber"),
                        datetime.now().date(),
                        order_data.get("customerName"),
                        item.get("productName"),
                        item.get("quantity"),
                        item.get("unitPrice") * item.get("quantity"),
                        item.get("vatAmount", 0),
                        (item.get("unitPrice") * item.get("quantity")) + item.get("vatAmount", 0)
                    )

                synced_ids.append(order_data.get("id"))
            except Exception as e:
                print(f"Error syncing order {order_data.get('id')}: {str(e)}")

    return {
        "synced_count": len(synced_ids),
        "synced_local_ids": synced_ids,
        "status": "success" if len(synced_ids) == len(body) else "partial_success"
    }
