-- Shopper platform: bilingual master data + RLS safety net on shared Postgres.
-- Application must execute per request: SET LOCAL app.tenant_id = '<uuid>';

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

CREATE SCHEMA IF NOT EXISTS platform;
CREATE SCHEMA IF NOT EXISTS tenant_data;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'shopper_app') THEN
        CREATE ROLE shopper_app LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'shopper_migrate') THEN
        CREATE ROLE shopper_migrate LOGIN;
    END IF;
END
$$;

ALTER ROLE shopper_migrate BYPASSRLS;

-- ---------------------------------------------------------------------------
-- Platform registry (resolved from subdomain → tenant id at the edge/API)
-- ---------------------------------------------------------------------------
CREATE TABLE platform.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subdomain CITEXT NOT NULL UNIQUE,
    display_name_en TEXT NOT NULL,
    display_name_bn TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'suspended', 'deleted')),
    dedicated_database_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tenants_subdomain_format CHECK (
        subdomain ~ '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'
    )
);

CREATE INDEX idx_tenants_status ON platform.tenants (status);

CREATE OR REPLACE FUNCTION platform.touch_tenants_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON platform.tenants
    FOR EACH ROW
    EXECUTE PROCEDURE platform.touch_tenants_updated_at();

-- ---------------------------------------------------------------------------
-- Bilingual master data (tenant-scoped)
-- ---------------------------------------------------------------------------
CREATE TABLE tenant_data.customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_bn TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    billing_address_en TEXT,
    billing_address_bn TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

CREATE TABLE tenant_data.product_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    name_en TEXT NOT NULL,
    name_bn TEXT NOT NULL,
    slug CITEXT NOT NULL,
    parent_id UUID REFERENCES tenant_data.product_categories (id) ON DELETE SET NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug)
);

CREATE TABLE tenant_data.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    category_id UUID REFERENCES tenant_data.product_categories (id) ON DELETE SET NULL,
    sku TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_bn TEXT NOT NULL,
    description_en TEXT,
    description_bn TEXT,
    unit TEXT NOT NULL DEFAULT 'pcs',
    buy_price NUMERIC(18, 4),
    sell_price NUMERIC(18, 4),
    mrp NUMERIC(18, 4),
    vat_rate_pct NUMERIC(5, 2) NOT NULL DEFAULT 0,
    barcode TEXT,
    qr_payload TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, sku)
);

CREATE INDEX idx_products_tenant ON tenant_data.products (tenant_id);
CREATE INDEX idx_products_tenant_active ON tenant_data.products (tenant_id) WHERE is_active;
CREATE INDEX idx_categories_tenant ON tenant_data.product_categories (tenant_id);
CREATE INDEX idx_customers_tenant ON tenant_data.customers (tenant_id);

-- ---------------------------------------------------------------------------
-- Row-Level Security (safety net: wrong/missing tenant GUC ⇒ no rows)
-- ---------------------------------------------------------------------------
ALTER TABLE tenant_data.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.product_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.products FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.product_categories FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.customers FORCE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION tenant_data.app_tenant_id()
RETURNS uuid AS $$
DECLARE
    raw TEXT;
BEGIN
    raw := NULLIF(btrim(current_setting('app.tenant_id', true)), '');
    IF raw IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN raw::uuid;
EXCEPTION
    WHEN invalid_text_representation THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE POLICY tenant_isolation_customers
    ON tenant_data.customers
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

CREATE POLICY tenant_isolation_categories
    ON tenant_data.product_categories
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

CREATE POLICY tenant_isolation_products
    ON tenant_data.products
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

-- ---------------------------------------------------------------------------
-- Grants (application role is not superuser; RLS enforced for shopper_app)
-- ---------------------------------------------------------------------------
GRANT USAGE ON SCHEMA platform TO shopper_app;
GRANT USAGE ON SCHEMA tenant_data TO shopper_app;
GRANT SELECT ON platform.tenants TO shopper_app;

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.customers TO shopper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.product_categories TO shopper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.products TO shopper_app;

GRANT ALL ON SCHEMA platform TO shopper_migrate;
GRANT ALL ON SCHEMA tenant_data TO shopper_migrate;
GRANT ALL ON ALL TABLES IN SCHEMA platform TO shopper_migrate;
GRANT ALL ON ALL TABLES IN SCHEMA tenant_data TO shopper_migrate;
GRANT ALL ON ALL SEQUENCES IN SCHEMA platform TO shopper_migrate;
GRANT ALL ON ALL SEQUENCES IN SCHEMA tenant_data TO shopper_migrate;

ALTER DEFAULT PRIVILEGES IN SCHEMA tenant_data
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO shopper_app;

-- Mushak-oriented reporting tables (bilingual headers + line facts) — minimal stub
CREATE TABLE tenant_data.vat_sales_register_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    mushak_form TEXT NOT NULL CHECK (mushak_form IN ('6.1', '6.2', '6.3', '6.6')),
    invoice_no TEXT NOT NULL,
    invoice_date DATE NOT NULL,
    buyer_name_en TEXT,
    buyer_name_bn TEXT,
    tin TEXT,
    hs_code TEXT,
    description_en TEXT,
    description_bn TEXT,
    qty NUMERIC(18, 4) NOT NULL,
    taxable_value NUMERIC(18, 4) NOT NULL,
    vat_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE tenant_data.vat_sales_register_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.vat_sales_register_lines FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_vat_sales
    ON tenant_data.vat_sales_register_lines
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.vat_sales_register_lines TO shopper_app;
GRANT ALL ON tenant_data.vat_sales_register_lines TO shopper_migrate;

-- Seed example tenant (optional dev)
INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
VALUES ('demo', 'Demo Traders Ltd.', 'ডেমো ট্রেডার্স লিমিটেড', 'active')
ON CONFLICT (subdomain) DO NOTHING;

INSERT INTO tenant_data.products (tenant_id, sku, name_en, name_bn, sell_price, vat_rate_pct)
SELECT t.id, 'SKU-1', 'Rice 1 kg', 'চাল ১ কেজি', 120.00, 15
FROM platform.tenants t
WHERE t.subdomain = 'demo'
ON CONFLICT (tenant_id, sku) DO NOTHING;
