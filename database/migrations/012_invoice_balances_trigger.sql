-- database/migrations/012_invoice_balances_trigger.sql
-- Trigger to automatically recalculate invoice outstanding balances whenever a payment is inserted, updated, or deleted.

CREATE OR REPLACE FUNCTION tenant_data.recalculate_invoice_balance()
RETURNS trigger AS $$
DECLARE
    v_invoice_id UUID;
    v_total NUMERIC;
    v_paid NUMERIC;
BEGIN
    v_invoice_id := COALESCE(NEW.invoice_id, OLD.invoice_id);

    IF v_invoice_id IS NOT NULL THEN
        -- Get total assigned so far
        SELECT COALESCE(SUM(amount), 0) INTO v_paid
        FROM tenant_data.payments
        WHERE invoice_id = v_invoice_id
          AND status = 'completed';

        -- Update invoice
        UPDATE tenant_data.invoices
        SET amount_paid = v_paid,
            balance_due = total_amount - v_paid,
            status = CASE
                WHEN (total_amount - v_paid) <= 0 THEN 'paid'
                WHEN v_paid > 0 THEN 'partially_paid'
                ELSE 'draft'
            END,
            updated_at = now()
        WHERE id = v_invoice_id;
    END IF;

    RETURN NULL; -- AFTER trigger, returning NULL is fine
END;
$$ LANGUAGE plpgsql;

-- We assign this trigger to the payments table
DROP TRIGGER IF EXISTS trg_recalculate_invoice_balance ON tenant_data.payments;
CREATE TRIGGER trg_recalculate_invoice_balance
    AFTER INSERT OR UPDATE OR DELETE
    ON tenant_data.payments
    FOR EACH ROW
    EXECUTE FUNCTION tenant_data.recalculate_invoice_balance();
