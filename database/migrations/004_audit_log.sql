-- Idempotent: safe via database/run_migrations.py.
-- Append-only audit trail for financial/stock/price changes.

CREATE TABLE IF NOT EXISTS tenant_data.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by TEXT,  -- e.g., user_id or 'system'
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_tenant_table ON tenant_data.audit_log (tenant_id, table_name);
CREATE INDEX idx_audit_record ON tenant_data.audit_log (record_id);

ALTER TABLE tenant_data.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.audit_log FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_audit
    ON tenant_data.audit_log
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT ON tenant_data.audit_log TO shopper_app;
GRANT ALL ON tenant_data.audit_log TO shopper_migrate;