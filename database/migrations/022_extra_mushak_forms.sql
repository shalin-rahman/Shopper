-- Mushak compliance enhancements: 6.7 (Credit Note), 6.8 (Debit Note), 6.5 (Internal Transfer)

-- Sales Returns (Decreasing Adjustments)
CREATE TABLE IF NOT EXISTS tenant_data.credit_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES tenant_data.invoices (id) ON DELETE CASCADE,
    note_no TEXT NOT NULL, -- e.g., 'CN-2024-001'
    reason TEXT,
    adjustment_amount_taxable NUMERIC(18, 4) NOT NULL,
    adjustment_amount_vat NUMERIC(18, 4) NOT NULL,
    total_adjustment NUMERIC(18, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, note_no)
);

-- Purchase Returns (Increasing/Decreasing Adjustments for Purchases)
CREATE TABLE IF NOT EXISTS tenant_data.debit_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    reference_id UUID, -- Optional link to Purchase Order or Invoice
    note_no TEXT NOT NULL,
    reason TEXT,
    adjustment_amount_taxable NUMERIC(18, 4) NOT NULL,
    adjustment_amount_vat NUMERIC(18, 4) NOT NULL,
    total_adjustment NUMERIC(18, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, note_no)
);

-- Internal Transfers (Mushak 6.5)
CREATE TABLE IF NOT EXISTS tenant_data.inventory_transfers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    transfer_no TEXT NOT NULL,
    from_location TEXT NOT NULL,
    to_location TEXT NOT NULL,
    total_value_taxable NUMERIC(18, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, transfer_no)
);

ALTER TABLE tenant_data.credit_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.credit_notes FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_cn ON tenant_data.credit_notes FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());

ALTER TABLE tenant_data.debit_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.debit_notes FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_dn ON tenant_data.debit_notes FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());

ALTER TABLE tenant_data.inventory_transfers ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.inventory_transfers FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_it ON tenant_data.inventory_transfers FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE ON tenant_data.credit_notes TO shopper_app;
GRANT SELECT, INSERT, UPDATE ON tenant_data.debit_notes TO shopper_app;
GRANT SELECT, INSERT, UPDATE ON tenant_data.inventory_transfers TO shopper_app;
