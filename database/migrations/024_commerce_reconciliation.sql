-- Persist offline order references, buyer details, discounts, and sales-return lines.

ALTER TABLE tenant_data.invoices
    ADD COLUMN IF NOT EXISTS discount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS buyer_name_en TEXT,
    ADD COLUMN IF NOT EXISTS phone TEXT,
    ADD COLUMN IF NOT EXISTS source_order_id TEXT;

ALTER TABLE tenant_data.vat_sales_register_lines
    ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(18, 4) NOT NULL DEFAULT 0;

ALTER TABLE tenant_data.credit_notes
    ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(18, 4) NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_source_order
    ON tenant_data.invoices (tenant_id, source_order_id)
    WHERE source_order_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS tenant_data.credit_note_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    credit_note_id UUID NOT NULL REFERENCES tenant_data.credit_notes (id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES tenant_data.invoices (id) ON DELETE CASCADE,
    invoice_line_id UUID NOT NULL REFERENCES tenant_data.invoice_lines (id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES tenant_data.products (id) ON DELETE RESTRICT,
    qty NUMERIC(18, 4) NOT NULL CHECK (qty > 0),
    unit_price NUMERIC(18, 4) NOT NULL,
    vat_rate_pct NUMERIC(5, 2) NOT NULL DEFAULT 0,
    taxable_amount NUMERIC(18, 4) NOT NULL,
    vat_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_credit_note_lines_invoice
    ON tenant_data.credit_note_lines (invoice_id, invoice_line_id);

ALTER TABLE tenant_data.credit_note_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.credit_note_lines FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_credit_note_lines ON tenant_data.credit_note_lines;
CREATE POLICY tenant_isolation_credit_note_lines
    ON tenant_data.credit_note_lines
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.credit_note_lines TO shopper_app;
GRANT ALL ON tenant_data.credit_note_lines TO shopper_migrate;
