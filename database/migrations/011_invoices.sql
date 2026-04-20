-- database/migrations/011_invoices.sql
-- Implements commercial invoicing with installment tracking and line-item VAT.

CREATE TABLE IF NOT EXISTS tenant_data.invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    customer_id UUID REFERENCES tenant_data.customers (id) ON DELETE SET NULL,
    invoice_no TEXT NOT NULL,
    subtotal NUMERIC(18, 4) NOT NULL DEFAULT 0,
    total_vat NUMERIC(18, 4) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    amount_paid NUMERIC(18, 4) NOT NULL DEFAULT 0,
    balance_due NUMERIC(18, 4) NOT NULL DEFAULT 0,
    installments JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft' 
        CHECK (status IN ('draft', 'partially_paid', 'paid', 'cancelled')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, invoice_no)
);

CREATE TABLE IF NOT EXISTS tenant_data.invoice_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES tenant_data.invoices (id) ON DELETE CASCADE,
    product_id UUID REFERENCES tenant_data.products (id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    qty NUMERIC(18, 4) NOT NULL DEFAULT 1,
    unit_price NUMERIC(18, 4) NOT NULL DEFAULT 0,
    vat_rate_pct NUMERIC(5, 2) NOT NULL DEFAULT 0,
    vat_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    line_total NUMERIC(18, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Link payments to invoices for reconciliation
ALTER TABLE tenant_data.payments ADD COLUMN IF NOT EXISTS invoice_id UUID REFERENCES tenant_data.invoices (id) ON DELETE SET NULL;

-- Indexes
CREATE INDEX idx_invoices_tenant ON tenant_data.invoices (tenant_id);
CREATE INDEX idx_invoices_customer ON tenant_data.invoices (customer_id);
CREATE INDEX idx_invoice_lines_invoice ON tenant_data.invoice_lines (invoice_id);

-- RLS
ALTER TABLE tenant_data.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.invoices FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.invoice_lines FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_invoices
    ON tenant_data.invoices
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

CREATE POLICY tenant_isolation_invoice_lines
    ON tenant_data.invoice_lines
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.invoices TO shopper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.invoice_lines TO shopper_app;
GRANT ALL ON tenant_data.invoices TO shopper_migrate;
GRANT ALL ON tenant_data.invoice_lines TO shopper_migrate;
