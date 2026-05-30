import asyncio
import json
import os
import sys
from decimal import Decimal

import asyncpg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_from_json(json_path: str, db_url: str):
    if not os.path.exists(json_path):
        print(f"Error: File not found {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conn = await asyncpg.connect(db_url)
    try:
        for tenant_data in data.get("tenants", []):
            subdomain = tenant_data["subdomain"]
            print(f"--- Seeding Tenant: {subdomain} ---")

            # 1. Tenant
            tenant = await conn.fetchrow(
                """
                INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
                VALUES ($1, $2, $3, 'active')
                ON CONFLICT (subdomain) DO UPDATE SET display_name_en = EXCLUDED.display_name_en
                RETURNING id
                """,
                subdomain, tenant_data["display_name_en"], tenant_data["display_name_bn"]
            )
            tenant_id = tenant["id"]

            # 2. Settings
            s = tenant_data.get("settings", {})
            await conn.execute(
                """
                INSERT INTO platform.tenant_settings (tenant_id, legal_title_en, bin, default_language)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id) DO UPDATE SET bin = EXCLUDED.bin
                """,
                tenant_id, s.get("legal_title_en"), s.get("bin"), s.get("default_language", "en")
            )

            # 3. Accounts
            print("  Provisioning Accounts...")
            await conn.execute("SELECT tenant_data.provision_system_accounts($1)", tenant_id)

            # 4. Staff
            print("  Seeding Staff...")
            for staff in tenant_data.get("staff", []):
                h = pwd_context.hash(staff["password"])
                await conn.execute(
                    """
                    INSERT INTO tenant_data.staff (tenant_id, username, password_hash, full_name, role)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (tenant_id, username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                    """,
                    tenant_id, staff["username"], h, staff["full_name"], staff["role"]
                )

            # 5. Suppliers
            print("  Seeding Suppliers...")
            for sup in tenant_data.get("suppliers", []):
                await conn.execute(
                    """
                    INSERT INTO tenant_data.suppliers (tenant_id, name, contact_name, phone, email)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (tenant_id, name) DO NOTHING
                    """,
                    tenant_id, sup["name"], sup.get("contact_name"), sup.get("phone"), sup.get("email")
                )

            # 6. Customers
            print("  Seeding Customers...")
            for cust in tenant_data.get("customers", []):
                await conn.execute(
                    """
                    INSERT INTO tenant_data.customers (tenant_id, name, phone, email, is_credit_allowed)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (tenant_id, phone) DO NOTHING
                    """,
                    tenant_id, cust["name"], cust["phone"], cust.get("email"), cust.get("is_credit_allowed", False)
                )

            # 7. Categories
            print("  Seeding Categories...")
            cat_map = {}
            for cat in tenant_data.get("categories", []):
                row = await conn.fetchrow(
                    """
                    INSERT INTO tenant_data.product_categories (tenant_id, name_en, name_bn, slug)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (tenant_id, slug) DO UPDATE SET name_en = EXCLUDED.name_en
                    RETURNING id, slug
                    """,
                    tenant_id, cat["name_en"], cat["name_bn"], cat["slug"]
                )
                cat_map[row["slug"]] = row["id"]

            # 8. Products
            print("  Seeding Products...")
            for prod in tenant_data.get("products", []):
                cat_id = cat_map.get(prod.get("category_slug"))
                p_row = await conn.fetchrow(
                    """
                    INSERT INTO tenant_data.products (
                        tenant_id, category_id, sku, name_en, name_bn, buy_price, sell_price, vat_rate_pct, stock_quantity
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (tenant_id, sku) DO NOTHING
                    RETURNING id
                    """,
                    tenant_id, cat_id, prod["sku"], prod["name_en"], prod["name_bn"],
                    Decimal(str(prod["buy_price"])), Decimal(str(prod["sell_price"])),
                    Decimal(str(prod["vat_rate_pct"])), Decimal(str(prod["stock_quantity"]))
                )
                if p_row and prod.get("stock_quantity", 0) > 0:
                    await conn.execute(
                        """
                        INSERT INTO tenant_data.stock_transactions (tenant_id, product_id, transaction_type, quantity, unit_cost, reference_type, notes)
                        VALUES ($1, $2, 'in', $3, $4, 'manual', 'Seed Stock')
                        """,
                        tenant_id, p_row["id"], prod["stock_quantity"], Decimal(str(prod["buy_price"]))
                    )

            # 9. Expenses
            print("  Seeding Expenses...")
            for exp in tenant_data.get("expenses", []):
                await conn.execute(
                    """
                    INSERT INTO tenant_data.expenses (tenant_id, category, amount, notes, ledger_mapped)
                    VALUES ($1, $2, $3, $4, true)
                    """,
                    tenant_id, exp["category"], Decimal(str(exp["amount"])), exp.get("notes")
                )

        print("\n✅ Total Entity Seeding completed successfully.")
    finally:
        await conn.close()

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "database/sample_data.json"
    url = os.getenv("DATABASE_URL", "postgresql://shopper_app:shopper_app_change_me@localhost:5432/shopper")
    asyncio.run(seed_from_json(path, url))
