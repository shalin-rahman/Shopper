-- Idempotent: safe via database/run_migrations.py.
-- Subscription and billing for tenants.

CREATE TABLE IF NOT EXISTS platform.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'cancelled')),
    monthly_fee NUMERIC(10, 2) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.billing_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'BDT',
    description TEXT,
    transaction_date TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT ALL ON platform.subscriptions TO shopper_migrate;
GRANT ALL ON platform.billing_transactions TO shopper_migrate;