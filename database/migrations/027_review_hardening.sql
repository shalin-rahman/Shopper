-- Fixes from the 2026-10-23 review: audit chain ordering, missing FORCE RLS,
-- and a unique gateway order id per tenant. Safe to run more than once.
BEGIN;

-- Audit chain. Two inserts for the same tenant could read the same previous
-- hash, and changed_at ties made "the last row" unclear. Each insert now takes
-- a per-tenant lock first and then a sequence number, so sequence order is
-- chain order.
CREATE SEQUENCE IF NOT EXISTS tenant_data.audit_log_chain_seq;
ALTER TABLE tenant_data.audit_log ADD COLUMN IF NOT EXISTS chain_seq BIGINT;

-- Number existing rows in the order the old trigger used to find the last row.
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT id FROM tenant_data.audit_log
        WHERE chain_seq IS NULL
        ORDER BY changed_at, id
    LOOP
        UPDATE tenant_data.audit_log
        SET chain_seq = nextval('tenant_data.audit_log_chain_seq')
        WHERE id = r.id;
    END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_chain_seq
    ON tenant_data.audit_log (tenant_id, chain_seq DESC);

GRANT USAGE ON SEQUENCE tenant_data.audit_log_chain_seq TO shopper_app;
GRANT USAGE ON SEQUENCE tenant_data.audit_log_chain_seq TO shopper_migrate;

-- The content hash is the same as in 015, so old rows still verify.
CREATE OR REPLACE FUNCTION tenant_data.chain_audit_hash()
RETURNS TRIGGER AS $$
DECLARE
    prev_hash TEXT;
    content_text TEXT;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.tenant_id::text, 0));
    NEW.chain_seq := nextval('tenant_data.audit_log_chain_seq');

    SELECT current_hash INTO prev_hash
    FROM tenant_data.audit_log
    WHERE tenant_id = NEW.tenant_id
    ORDER BY chain_seq DESC
    LIMIT 1;

    NEW.previous_hash := COALESCE(prev_hash, 'GENESIS');

    content_text := NEW.tenant_id::text || '|' ||
                    NEW.table_name || '|' ||
                    NEW.record_id::text || '|' ||
                    NEW.action || '|' ||
                    COALESCE(NEW.old_values::text, '') || '|' ||
                    COALESCE(NEW.new_values::text, '') || '|' ||
                    NEW.previous_hash;

    NEW.current_hash := encode(digest(content_text, 'sha256'), 'hex');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Match the other tenant tables. Today the owners are superuser or BYPASSRLS,
-- so this only matters if ownership moves to an ordinary role.
ALTER TABLE tenant_data.suppliers FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.purchase_orders FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.po_lines FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.expense_categories FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.expenses FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.customer_collections FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.account_transfers FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.supplier_payments FORCE ROW LEVEL SECURITY;

-- One payment per gateway order id per tenant. Stop with a clear message if
-- old data already has duplicates; they need a manual look first.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM tenant_data.payments
        WHERE order_id IS NOT NULL
        GROUP BY tenant_id, gateway, order_id
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'tenant_data.payments has duplicate (tenant_id, gateway, order_id) rows; resolve them before applying 027';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_tenant_gateway_order
    ON tenant_data.payments (tenant_id, gateway, order_id)
    WHERE order_id IS NOT NULL;

COMMIT;
