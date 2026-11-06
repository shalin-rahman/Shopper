-- database/migrations/031_leftovers.sql
-- Debit notes get the PO and supplier columns the return code needs, and lose the duplicate policy from 023.
-- The unused inventory_transfers table goes, but only when it holds no rows.
-- Staff can have a home branch. Product audit rows skip updates that only change stock_quantity,
-- since stock_transactions already audits those. Refunds on gateway payments get their own table
-- and lower the invoice's paid amount.
-- Safe to rerun.

BEGIN;

ALTER TABLE tenant_data.debit_notes
    ADD COLUMN IF NOT EXISTS po_id UUID REFERENCES tenant_data.purchase_orders (id),
    ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES tenant_data.suppliers (id);

ALTER TABLE tenant_data.debit_notes
    ALTER COLUMN adjustment_amount_taxable SET DEFAULT 0,
    ALTER COLUMN adjustment_amount_vat SET DEFAULT 0,
    ALTER COLUMN total_adjustment SET DEFAULT 0;

-- Older notes only have reference_id. Fill the new columns where it names a PO.
UPDATE tenant_data.debit_notes dn
SET po_id = po.id,
    supplier_id = po.supplier_id
FROM tenant_data.purchase_orders po
WHERE dn.reference_id = po.id
  AND dn.po_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_debit_notes_po ON tenant_data.debit_notes (po_id);

DROP POLICY IF EXISTS tenant_isolation_debit_notes ON tenant_data.debit_notes;
DROP POLICY IF EXISTS tenant_isolation_dn ON tenant_data.debit_notes;
CREATE POLICY tenant_isolation_dn
    ON tenant_data.debit_notes
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

REVOKE DELETE ON tenant_data.debit_notes FROM shopper_app;

-- With row security off, a role that RLS would filter gets an error here instead of a
-- false "empty" that would drop real rows.
SET LOCAL row_security = off;

DO $$
BEGIN
    IF to_regclass('tenant_data.inventory_transfers') IS NULL THEN
        RETURN;
    END IF;
    IF EXISTS (SELECT 1 FROM tenant_data.inventory_transfers) THEN
        RAISE NOTICE 'tenant_data.inventory_transfers has rows; left in place';
    ELSE
        DROP TABLE tenant_data.inventory_transfers;
    END IF;
END;
$$;

SET LOCAL row_security = on;

-- NULL means the tenant's main branch.
ALTER TABLE tenant_data.staff ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES tenant_data.branches (id);

DROP TRIGGER IF EXISTS trg_audit_products ON tenant_data.products;
CREATE TRIGGER trg_audit_products
    AFTER INSERT OR DELETE ON tenant_data.products
    FOR EACH ROW EXECUTE PROCEDURE tenant_data.audit_row_change_fn();

DROP TRIGGER IF EXISTS trg_audit_products_update ON tenant_data.products;
CREATE TRIGGER trg_audit_products_update
    AFTER UPDATE ON tenant_data.products
    FOR EACH ROW
    WHEN ((to_jsonb(OLD) - 'stock_quantity') IS DISTINCT FROM (to_jsonb(NEW) - 'stock_quantity'))
    EXECUTE PROCEDURE tenant_data.audit_row_change_fn();

CREATE TABLE IF NOT EXISTS tenant_data.payment_refunds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    payment_id UUID NOT NULL REFERENCES tenant_data.payments (id),
    invoice_id UUID REFERENCES tenant_data.invoices (id),
    amount NUMERIC(18, 4) NOT NULL CHECK (amount > 0),
    reference TEXT,
    note TEXT,
    credit_note_id UUID REFERENCES tenant_data.credit_notes (id),
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payment_refunds_payment ON tenant_data.payment_refunds (payment_id);
CREATE INDEX IF NOT EXISTS idx_payment_refunds_invoice ON tenant_data.payment_refunds (invoice_id);

ALTER TABLE tenant_data.payment_refunds ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.payment_refunds FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_payment_refunds ON tenant_data.payment_refunds;
CREATE POLICY tenant_isolation_payment_refunds
    ON tenant_data.payment_refunds
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT ON tenant_data.payment_refunds TO shopper_app;
GRANT ALL ON tenant_data.payment_refunds TO shopper_migrate;

DROP TRIGGER IF EXISTS trg_audit_payment_refunds ON tenant_data.payment_refunds;
CREATE TRIGGER trg_audit_payment_refunds
    AFTER INSERT OR UPDATE OR DELETE ON tenant_data.payment_refunds
    FOR EACH ROW EXECUTE PROCEDURE tenant_data.audit_row_change_fn();

-- Same as 026, less refunds. An invoice whose payments were all refunded goes back to
-- issued, not draft: its stock was already taken when it was issued.
CREATE OR REPLACE FUNCTION tenant_data.refresh_invoice_balance(p_invoice_id UUID)
RETURNS void AS $$
DECLARE
    v_paid NUMERIC;
BEGIN
    SELECT
        COALESCE((
            SELECT SUM(amount)
            FROM tenant_data.payments
            WHERE invoice_id = p_invoice_id
              AND status = 'completed'
        ), 0)
        +
        COALESCE((
            SELECT SUM(amount)
            FROM tenant_data.invoice_settlements
            WHERE invoice_id = p_invoice_id
              AND status = 'completed'
        ), 0)
        -
        COALESCE((
            SELECT SUM(r.amount)
            FROM tenant_data.payment_refunds r
            JOIN tenant_data.payments p ON p.id = r.payment_id
            WHERE r.invoice_id = p_invoice_id
              AND p.status = 'completed'
        ), 0)
    INTO v_paid;

    UPDATE tenant_data.invoices
    SET amount_paid = v_paid,
        balance_due = GREATEST(total_amount - v_paid, 0),
        status = CASE
            WHEN status = 'cancelled' THEN 'cancelled'
            WHEN total_amount - v_paid <= 0 THEN 'paid'
            WHEN v_paid > 0 THEN 'partially_paid'
            WHEN status = 'draft' THEN 'draft'
            ELSE 'issued'
        END,
        updated_at = now()
    WHERE id = p_invoice_id;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recalculate_invoice_refund_balance ON tenant_data.payment_refunds;
CREATE TRIGGER trg_recalculate_invoice_refund_balance
    AFTER INSERT OR UPDATE OR DELETE
    ON tenant_data.payment_refunds
    FOR EACH ROW
    EXECUTE FUNCTION tenant_data.recalculate_invoice_balance();

COMMIT;
