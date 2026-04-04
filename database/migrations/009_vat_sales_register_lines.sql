-- Idempotent: mirrors init schema for DBs that only ran migrations.

CREATE TABLE IF NOT EXISTS tenant_data.vat_sales_register_lines (
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

DROP POLICY IF EXISTS tenant_isolation_vat_sales ON tenant_data.vat_sales_register_lines;
CREATE POLICY tenant_isolation_vat_sales
    ON tenant_data.vat_sales_register_lines
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.vat_sales_register_lines TO shopper_app;
GRANT ALL ON tenant_data.vat_sales_register_lines TO shopper_migrate;
