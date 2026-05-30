import json
import asyncio
import asyncpg
import os
from decimal import Decimal

# Configuration - pull from environment or use defaults
DB_URL = os.getenv("DATABASE_URL", "postgresql://shopper_admin:shopper_vault_2025@localhost:5432/shopper_platform")
DATA_FILE = "database/full_test_data.json"

async def seed():
    print(f"🚀 Starting database seed from {DATA_FILE}...")
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conn = await asyncpg.connect(DB_URL)
    
    try:
        for t in data['tenants']:
            print(f"📦 Seeding tenant: {t['subdomain']}")
            
            # 1. Create Tenant (Platform level)
            tenant = await conn.fetchrow(
                """
                INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
                VALUES ($1, $2, $3, 'active')
                ON CONFLICT (subdomain) DO UPDATE SET display_name_en = EXCLUDED.display_name_en
                RETURNING id
                """,
                t['subdomain'], t['display_name_en'], t['display_name_bn']
            )
            tenant_id = tenant['id']

            # 2. Settings
            s = t.get('settings', {})
            await conn.execute(
                """
                INSERT INTO platform.tenant_settings (tenant_id, legal_title_en, bin, default_language)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id) DO UPDATE SET legal_title_en = EXCLUDED.legal_title_en
                """,
                tenant_id, s.get('legal_title_en'), s.get('bin'), s.get('default_language', 'en')
            )

            # 3. Staff
            for staff in t.get('staff', []):
                await conn.execute(
                    """
                    INSERT INTO platform.staff_members (tenant_id, username, password_hash, full_name, role, is_active)
                    VALUES ($1, $2, $3, $4, $5, true)
                    ON CONFLICT (tenant_id, username) DO NOTHING
                    """,
                    tenant_id, staff['username'], "hashed_password_placeholder", staff['full_name'], staff['role']
                )

            # 4. Categories & Products
            for cat in t.get('categories', []):
                await conn.execute(
                    "INSERT INTO tenant_data.categories (tenant_id, name_en, name_bn, slug) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
                    tenant_id, cat['name_en'], cat['name_bn'], cat['slug']
                )

            for prod in t.get('products', []):
                # Simple logic: assume category exists or is null
                await conn.execute(
                    """
                    INSERT INTO tenant_data.products (tenant_id, sku, name_en, name_bn, buy_price, sell_price, vat_rate_pct, stock_quantity)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (tenant_id, sku) DO UPDATE SET stock_quantity = EXCLUDED.stock_quantity
                    """,
                    tenant_id, prod['sku'], prod['name_en'], prod['name_bn'], 
                    Decimal(str(prod['buy_price'])), Decimal(str(prod['sell_price'])), 
                    Decimal(str(prod['vat_rate_pct'])), Decimal(str(prod['stock_quantity']))
                )

            print(f"✅ Success for {t['subdomain']}")

    finally:
        await conn.close()
        print("🏁 Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed())
