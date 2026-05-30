-- database/migrations/019_suppliers_po.sql
-- Completes the supply chain cycle: Buying from suppliers via Purchase Orders.

CREATE TABLE IF NOT EXISTS tenant_data.suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_bn TEXT NOT NULL,
    contact_person TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

CREATE TABLE IF NOT EXISTS tenant_data.purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES tenant_data.suppliers (id),
    po_no TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'received', 'canceled')),
    total_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, po_no)
);

CREATE TABLE IF NOT EXISTS tenant_data.po_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    po_id UUID NOT NULL REFERENCES tenant_data.purchase_orders (id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES tenant_data.products (id),
    qty NUMERIC(18, 4) NOT NULL,
    unit_cost NUMERIC(18, 4) NOT NULL,
    line_total NUMERIC(18, 4) NOT NULL
);

-- RLS & Grants
ALTER TABLE tenant_data.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.po_lines ENABLE ROW LEVEL SECURITY;

-- Assuming function app_tenant_id() exists in tenant_data
CREATE POLICY tenant_isolation_suppliers ON tenant_data.suppliers FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());
CREATE POLICY tenant_isolation_po ON tenant_data.purchase_orders FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());
CREATE POLICY tenant_isolation_po_lines ON tenant_data.po_lines FOR ALL TO shopper_app USING (tenant_id = (SELECT tenant_id FROM tenant_data.purchase_orders WHERE id = po_id));

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.suppliers TO shopper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.purchase_orders TO shopper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.po_lines TO shopper_app;
