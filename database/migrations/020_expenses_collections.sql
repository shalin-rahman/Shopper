-- database/migrations/020_expenses_collections.sql
-- Completes the business cycle with Expense tracking and Credit Collections.

CREATE TABLE IF NOT EXISTS tenant_data.expense_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    name_en TEXT NOT NULL,
    name_bn TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name_en)
);

CREATE TABLE IF NOT EXISTS tenant_data.expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES tenant_data.expense_categories (id),
    amount NUMERIC(18, 4) NOT NULL,
    description TEXT,
    staff_id UUID REFERENCES tenant_data.staff (id),
    expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Collection: Receiving payment from a customer to pay down their "account balance" (Outstanding debt)
-- This is different from POS payments which are tied to a single invoice at the time of sale.
CREATE TABLE IF NOT EXISTS tenant_data.customer_collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES tenant_data.customers (id),
    amount NUMERIC(18, 4) NOT NULL,
    payment_method TEXT NOT NULL CHECK (payment_method IN ('cash', 'bkash', 'nagad', 'bank')),
    reference_no TEXT,
    notes TEXT,
    collected_by UUID REFERENCES tenant_data.staff (id),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS & Grants
ALTER TABLE tenant_data.expense_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.customer_collections ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_expenses_cat ON tenant_data.expense_categories FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());
CREATE POLICY tenant_isolation_expenses ON tenant_data.expenses FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());
CREATE POLICY tenant_isolation_collections ON tenant_data.customer_collections FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.expense_categories TO shopper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.expenses TO shopper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.customer_collections TO shopper_app;

-- Trigger to update customer balance automatically when a collection is recorded
CREATE OR REPLACE FUNCTION tenant_data.apply_customer_collection()
RETURNS TRIGGER AS $$
BEGIN
    -- This assumes current_balance is updated elsewhere (e.g. daily sync)
    -- But for real-time ledger, we should insert into ledger_entries
    INSERT INTO tenant_data.ledger_entries (tenant_id, account_code, credit, description, reference_type, reference_id)
    VALUES (NEW.tenant_id, 'AR-CUSTOMER-' || NEW.customer_id, NEW.amount, 'Collection: ' || NEW.payment_method, 'collection', NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customer_collection_ledger
    AFTER INSERT ON tenant_data.customer_collections
    FOR EACH ROW
    EXECUTE PROCEDURE tenant_data.apply_customer_collection();
