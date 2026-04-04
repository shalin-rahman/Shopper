-- Idempotent: safe via database/run_migrations.py.
-- Basic ERP stock management: in/out transactions, inventory valuation.

CREATE TABLE IF NOT EXISTS tenant_data.stock_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES tenant_data.products (id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('in', 'out', 'adjustment')),
    quantity NUMERIC(18, 4) NOT NULL,
    unit_cost NUMERIC(18, 4),
    reference_type TEXT,  -- e.g., 'purchase', 'sale', 'manual'
    reference_id UUID,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_stock_tenant_product ON tenant_data.stock_transactions (tenant_id, product_id);
CREATE INDEX idx_stock_reference ON tenant_data.stock_transactions (reference_type, reference_id);

ALTER TABLE tenant_data.stock_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.stock_transactions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_stock
    ON tenant_data.stock_transactions
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE ON tenant_data.stock_transactions TO shopper_app;
GRANT ALL ON tenant_data.stock_transactions TO shopper_migrate;