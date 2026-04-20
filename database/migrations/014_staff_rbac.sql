-- database/migrations/014_staff_rbac.sql
-- Staff management and RBAC.

CREATE TYPE tenant_data.staff_role AS ENUM ('cashier', 'manager', 'accountant', 'admin');

CREATE TABLE tenant_data.staff (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role tenant_data.staff_role NOT NULL DEFAULT 'cashier',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, username)
);

ALTER TABLE tenant_data.staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.staff FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_staff
    ON tenant_data.staff
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.staff TO shopper_app;
