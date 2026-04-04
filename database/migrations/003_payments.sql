-- Idempotent: safe via database/run_migrations.py.
-- Payments table for checkout gateways (SSLCommerz, bKash, etc.) with IPN idempotency.

CREATE TABLE IF NOT EXISTS tenant_data.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    gateway TEXT NOT NULL CHECK (gateway IN ('sslcommerz', 'bkash', 'nagad', 'rocket')),
    amount NUMERIC(18, 4) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'BDT',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'cancelled')),
    gateway_transaction_id TEXT,
    description TEXT,
    order_id TEXT,
    ipn_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, gateway_transaction_id)  -- idempotency per gateway
);

CREATE INDEX idx_payments_tenant ON tenant_data.payments (tenant_id);
CREATE INDEX idx_payments_status ON tenant_data.payments (status);

ALTER TABLE tenant_data.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.payments FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_payments
    ON tenant_data.payments
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE ON tenant_data.payments TO shopper_app;
GRANT ALL ON tenant_data.payments TO shopper_migrate;