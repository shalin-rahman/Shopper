-- database/migrations/030_branch_stock.sql
-- Stock per branch. Each tenant gets a main branch that holds all stock it had before.
-- products.stock_quantity stays as the total over branches, kept by a trigger on stock_levels.
-- Cost layers and WAC stay tenant-wide. Transfers use their own types so the FIFO trigger skips them.
-- Safe to rerun.

BEGIN;

CREATE TABLE IF NOT EXISTS tenant_data.branches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    is_main BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_branches_one_main ON tenant_data.branches (tenant_id) WHERE is_main;

ALTER TABLE tenant_data.branches ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.branches FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_branches ON tenant_data.branches;
CREATE POLICY tenant_isolation_branches
    ON tenant_data.branches
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE ON tenant_data.branches TO shopper_app;
GRANT ALL ON tenant_data.branches TO shopper_migrate;

CREATE TABLE IF NOT EXISTS tenant_data.stock_levels (
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES tenant_data.branches (id),
    product_id UUID NOT NULL REFERENCES tenant_data.products (id) ON DELETE CASCADE,
    quantity NUMERIC(18, 4) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (branch_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_stock_levels_product ON tenant_data.stock_levels (product_id);

ALTER TABLE tenant_data.stock_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.stock_levels FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_stock_levels ON tenant_data.stock_levels;
CREATE POLICY tenant_isolation_stock_levels
    ON tenant_data.stock_levels
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE ON tenant_data.stock_levels TO shopper_app;
GRANT ALL ON tenant_data.stock_levels TO shopper_migrate;

INSERT INTO tenant_data.branches (tenant_id, name, code, is_main)
SELECT t.id, 'Main branch', 'MAIN', true
FROM platform.tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_data.branches b WHERE b.tenant_id = t.id AND b.is_main
);

-- Runs before the sync trigger exists, so the totals are copied, not recomputed.
INSERT INTO tenant_data.stock_levels (tenant_id, branch_id, product_id, quantity)
SELECT p.tenant_id, b.id, p.id, p.stock_quantity
FROM tenant_data.products p
JOIN tenant_data.branches b ON b.tenant_id = p.tenant_id AND b.is_main
ON CONFLICT (branch_id, product_id) DO NOTHING;

ALTER TABLE tenant_data.stock_transactions
    ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES tenant_data.branches (id);

-- The audit trigger would log one row per old transaction for this backfill.
ALTER TABLE tenant_data.stock_transactions DISABLE TRIGGER trg_audit_stock_transactions;
UPDATE tenant_data.stock_transactions st
SET branch_id = b.id
FROM tenant_data.branches b
WHERE b.tenant_id = st.tenant_id AND b.is_main AND st.branch_id IS NULL;
ALTER TABLE tenant_data.stock_transactions ENABLE TRIGGER trg_audit_stock_transactions;

ALTER TABLE tenant_data.stock_transactions DROP CONSTRAINT IF EXISTS stock_transactions_transaction_type_check;
ALTER TABLE tenant_data.stock_transactions ADD CONSTRAINT stock_transactions_transaction_type_check
    CHECK (transaction_type IN (
        'in', 'out', 'adjustment', 'receive', 'return_in', 'gift_in',
        'damage', 'return_out', 'gift_out', 'expired',
        'transfer_out', 'transfer_in'
    ));

CREATE OR REPLACE FUNCTION tenant_data.sync_product_stock()
RETURNS trigger AS $$
DECLARE
    pid UUID;
BEGIN
    FOREACH pid IN ARRAY CASE TG_OP
        WHEN 'INSERT' THEN ARRAY[NEW.product_id]
        WHEN 'DELETE' THEN ARRAY[OLD.product_id]
        ELSE ARRAY[NEW.product_id, OLD.product_id]
    END
    LOOP
        UPDATE tenant_data.products
        SET stock_quantity = (SELECT COALESCE(SUM(quantity), 0)
                              FROM tenant_data.stock_levels WHERE product_id = pid)
        WHERE id = pid;
    END LOOP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_product_stock ON tenant_data.stock_levels;
CREATE TRIGGER trg_sync_product_stock
    AFTER INSERT OR UPDATE OR DELETE ON tenant_data.stock_levels
    FOR EACH ROW EXECUTE FUNCTION tenant_data.sync_product_stock();

-- On a rerun the backfill skips rows that exist, so fix any total that drifted.
UPDATE tenant_data.products p
SET stock_quantity = s.total
FROM (SELECT product_id, SUM(quantity) AS total
      FROM tenant_data.stock_levels GROUP BY product_id) s
WHERE s.product_id = p.id AND p.stock_quantity IS DISTINCT FROM s.total;

COMMIT;
