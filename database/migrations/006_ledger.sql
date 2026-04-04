-- Idempotent: safe via database/run_migrations.py.
-- Basic general ledger for AR/AP.

CREATE TABLE IF NOT EXISTS tenant_data.ledger_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    account_code TEXT NOT NULL,
    debit NUMERIC(18, 4) DEFAULT 0,
    credit NUMERIC(18, 4) DEFAULT 0,
    description TEXT,
    reference_type TEXT,
    reference_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ledger_tenant_account ON tenant_data.ledger_entries (tenant_id, account_code);

ALTER TABLE tenant_data.ledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.ledger_entries FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_ledger
    ON tenant_data.ledger_entries
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT ON tenant_data.ledger_entries TO shopper_app;
GRANT ALL ON tenant_data.ledger_entries TO shopper_migrate;