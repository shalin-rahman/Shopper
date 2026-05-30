-- database/migrations/023_procurement_lifecycle.sql
-- Adds Purchase Returns (Mushak 6.8) and Accounts Payable tracking.

-- 1. Purchase Returns (Debit Notes)
CREATE TABLE IF NOT EXISTS tenant_data.debit_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES tenant_data.suppliers (id),
    po_id UUID REFERENCES tenant_data.purchase_orders (id),
    note_no TEXT NOT NULL,
    reason TEXT,
    adjustment_amount_taxable NUMERIC(18, 4) NOT NULL DEFAULT 0,
    adjustment_amount_vat NUMERIC(18, 4) NOT NULL DEFAULT 0,
    total_adjustment NUMERIC(18, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, note_no)
);

-- 2. Extend Purchase Orders for balance tracking
ALTER TABLE tenant_data.purchase_orders 
ADD COLUMN IF NOT EXISTS amount_paid NUMERIC(18, 4) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS balance_due NUMERIC(18, 4) NOT NULL DEFAULT 0;

-- 3. Supplier Payments (Accounts Payable)
CREATE TABLE IF NOT EXISTS tenant_data.supplier_payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES tenant_data.suppliers (id),
    po_id UUID REFERENCES tenant_data.purchase_orders (id),
    payment_no TEXT NOT NULL,
    amount NUMERIC(18, 4) NOT NULL,
    payment_method TEXT NOT NULL, -- Cash, Bank, Check
    ref_no TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, payment_no)
);

-- RLS & Grants
ALTER TABLE tenant_data.debit_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.supplier_payments ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_debit_notes ON tenant_data.debit_notes FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());
CREATE POLICY tenant_isolation_supplier_payments ON tenant_data.supplier_payments FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.debit_notes TO shopper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.supplier_payments TO shopper_app;
