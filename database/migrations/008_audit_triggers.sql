-- Idempotent: audit_log DML triggers on key tenant_data tables.

CREATE OR REPLACE FUNCTION tenant_data.audit_row_change_fn()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
    v_tid UUID;
    v_rid UUID;
    v_old JSONB;
    v_new JSONB;
    v_actor TEXT;
BEGIN
    v_actor := COALESCE(
        NULLIF(BTRIM(COALESCE(current_setting('app.changed_by', true), '')), ''),
        'system'
    );

    IF TG_OP = 'DELETE' THEN
        v_tid := OLD.tenant_id;
        v_rid := OLD.id;
        v_old := row_to_json(OLD)::jsonb;
        v_new := NULL;
        INSERT INTO tenant_data.audit_log (tenant_id, table_name, record_id, action, old_values, new_values, changed_by)
        VALUES (
            v_tid,
            TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
            v_rid,
            TG_OP,
            v_old,
            v_new,
            v_actor
        );
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        v_tid := NEW.tenant_id;
        v_rid := NEW.id;
        v_old := row_to_json(OLD)::jsonb;
        v_new := row_to_json(NEW)::jsonb;
        INSERT INTO tenant_data.audit_log (tenant_id, table_name, record_id, action, old_values, new_values, changed_by)
        VALUES (
            v_tid,
            TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
            v_rid,
            TG_OP,
            v_old,
            v_new,
            v_actor
        );
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        v_tid := NEW.tenant_id;
        v_rid := NEW.id;
        v_old := NULL;
        v_new := row_to_json(NEW)::jsonb;
        INSERT INTO tenant_data.audit_log (tenant_id, table_name, record_id, action, old_values, new_values, changed_by)
        VALUES (
            v_tid,
            TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
            v_rid,
            TG_OP,
            v_old,
            v_new,
            v_actor
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$;

ALTER FUNCTION tenant_data.audit_row_change_fn() OWNER TO shopper_migrate;
REVOKE ALL ON FUNCTION tenant_data.audit_row_change_fn() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION tenant_data.audit_row_change_fn() TO shopper_app;

DROP TRIGGER IF EXISTS trg_audit_products ON tenant_data.products;
CREATE TRIGGER trg_audit_products
    AFTER INSERT OR UPDATE OR DELETE ON tenant_data.products
    FOR EACH ROW EXECUTE PROCEDURE tenant_data.audit_row_change_fn();

DROP TRIGGER IF EXISTS trg_audit_stock_transactions ON tenant_data.stock_transactions;
CREATE TRIGGER trg_audit_stock_transactions
    AFTER INSERT OR UPDATE OR DELETE ON tenant_data.stock_transactions
    FOR EACH ROW EXECUTE PROCEDURE tenant_data.audit_row_change_fn();

DROP TRIGGER IF EXISTS trg_audit_payments ON tenant_data.payments;
CREATE TRIGGER trg_audit_payments
    AFTER INSERT OR UPDATE OR DELETE ON tenant_data.payments
    FOR EACH ROW EXECUTE PROCEDURE tenant_data.audit_row_change_fn();

DROP TRIGGER IF EXISTS trg_audit_ledger_entries ON tenant_data.ledger_entries;
CREATE TRIGGER trg_audit_ledger_entries
    AFTER INSERT OR UPDATE OR DELETE ON tenant_data.ledger_entries
    FOR EACH ROW EXECUTE PROCEDURE tenant_data.audit_row_change_fn();
