-- database/seed_sample.sql
-- Seed data for a demo tenant 'demo'

INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
VALUES ('demo', 'Demo Store', 'ডেমো স্টোর', 'active')
ON CONFLICT (subdomain) DO NOTHING;

-- Get the tenant id (assuming fresh DB, but let's be safe)
-- Normally you'd get this via a variable, but for SQL script:
DO $$
DECLARE
    tid UUID;
BEGIN
    SELECT id INTO tid FROM platform.tenants WHERE subdomain = 'demo';
    
    -- Provision Settings
    INSERT INTO platform.tenant_settings (tenant_id, legal_title_en, bin)
    VALUES (tid, 'Shopper Demo Retail', '123456789-0101')
    ON CONFLICT (tenant_id) DO NOTHING;

    -- Provision Accounts
    PERFORM tenant_data.provision_system_accounts(tid);

    -- Provision Staff (admin/password)
    INSERT INTO tenant_data.staff (tenant_id, username, password_hash, full_name, role)
    VALUES (tid, 'admin', '$2b$12$R.S/V7N6.B0zP..s1e..S.e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1', 'System Admin', 'admin')
    ON CONFLICT (tenant_id, username) DO NOTHING;

    -- Add Categories
    INSERT INTO tenant_data.product_categories (tenant_id, name_en, name_bn, slug)
    VALUES 
        (tid, 'Electronics', 'ইলেকট্রনিক্স', 'electronics'),
        (tid, 'Groceries', 'মুদি মাল', 'groceries')
    ON CONFLICT (tenant_id, slug) DO NOTHING;

    -- Add Products
    INSERT INTO tenant_data.products (tenant_id, sku, name_en, name_bn, buy_price, sell_price, vat_rate_pct, stock_quantity)
    VALUES 
        (tid, 'PROD-001', 'Smart Watch GL', 'স্মার্ট ওয়াচ জিএল', 2500, 3200, 5, 20),
        (tid, 'PROD-002', 'Basmati Rice 5kg', 'বাসমতি চাল ৫ কেজি', 650, 780, 0, 100)
    ON CONFLICT (tenant_id, sku) DO NOTHING;

END $$;
