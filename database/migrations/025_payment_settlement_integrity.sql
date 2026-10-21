-- Keep invoice balances derived from the gateway payment and POS settlement ledgers.

CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_tenant_id_id
    ON tenant_data.invoices (tenant_id, id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tenant_data.invoice_lines'::regclass
          AND conname = 'invoice_lines_invoice_tenant_fk'
    ) THEN
        ALTER TABLE tenant_data.invoice_lines
            ADD CONSTRAINT invoice_lines_invoice_tenant_fk
            FOREIGN KEY (tenant_id, invoice_id)
            REFERENCES tenant_data.invoices (tenant_id, id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tenant_data.payments'::regclass
          AND conname = 'payments_invoice_tenant_fk'
    ) THEN
        ALTER TABLE tenant_data.payments
            ADD CONSTRAINT payments_invoice_tenant_fk
            FOREIGN KEY (tenant_id, invoice_id)
            REFERENCES tenant_data.invoices (tenant_id, id);
    END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS tenant_data.invoice_settlements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL,
    amount NUMERIC(18, 4) NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL CHECK (
        payment_method IN ('cash', 'bkash', 'nagad', 'rocket', 'bank', 'card', 'other', 'legacy')
    ),
    source TEXT NOT NULL CHECK (source IN ('pos', 'legacy_backfill')),
    source_reference TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'reversed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, source, source_reference),
    FOREIGN KEY (tenant_id, invoice_id)
        REFERENCES tenant_data.invoices (tenant_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invoice_settlements_invoice
    ON tenant_data.invoice_settlements (invoice_id, status);

ALTER TABLE tenant_data.invoice_settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.invoice_settlements FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_invoice_settlements
    ON tenant_data.invoice_settlements;
CREATE POLICY tenant_isolation_invoice_settlements
    ON tenant_data.invoice_settlements
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_data.invoice_settlements TO shopper_app;
GRANT ALL ON tenant_data.invoice_settlements TO shopper_migrate;

-- Preserve historical paid balances that predate the POS settlement ledger.
INSERT INTO tenant_data.invoice_settlements (
    tenant_id, invoice_id, amount, payment_method, source, source_reference
)
SELECT
    i.tenant_id,
    i.id,
    i.amount_paid - COALESCE(gateway_payments.amount, 0),
    'legacy',
    'legacy_backfill',
    i.id::text
FROM tenant_data.invoices AS i
LEFT JOIN LATERAL (
    SELECT SUM(p.amount) AS amount
    FROM tenant_data.payments AS p
    WHERE p.invoice_id = i.id
      AND p.status = 'completed'
) AS gateway_payments ON true
WHERE i.amount_paid > COALESCE(gateway_payments.amount, 0)
ON CONFLICT (tenant_id, source, source_reference) DO NOTHING;

DROP TRIGGER IF EXISTS trg_audit_invoice_settlements
    ON tenant_data.invoice_settlements;
CREATE TRIGGER trg_audit_invoice_settlements
    AFTER INSERT OR UPDATE OR DELETE
    ON tenant_data.invoice_settlements
    FOR EACH ROW
    EXECUTE FUNCTION tenant_data.audit_row_change_fn();

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
    INTO v_paid;

    UPDATE tenant_data.invoices
    SET amount_paid = v_paid,
        balance_due = GREATEST(total_amount - v_paid, 0),
        status = CASE
            WHEN status = 'cancelled' THEN 'cancelled'
            WHEN total_amount - v_paid <= 0 THEN 'paid'
            WHEN v_paid > 0 THEN 'partially_paid'
            ELSE 'draft'
        END,
        updated_at = now()
    WHERE id = p_invoice_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tenant_data.recalculate_invoice_balance()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM tenant_data.refresh_invoice_balance(NEW.invoice_id);
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM tenant_data.refresh_invoice_balance(OLD.invoice_id);
    ELSE
        PERFORM tenant_data.refresh_invoice_balance(OLD.invoice_id);
        IF NEW.invoice_id IS DISTINCT FROM OLD.invoice_id THEN
            PERFORM tenant_data.refresh_invoice_balance(NEW.invoice_id);
        END IF;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recalculate_invoice_balance ON tenant_data.payments;
CREATE TRIGGER trg_recalculate_invoice_balance
    AFTER INSERT OR UPDATE OR DELETE
    ON tenant_data.payments
    FOR EACH ROW
    EXECUTE FUNCTION tenant_data.recalculate_invoice_balance();

DROP TRIGGER IF EXISTS trg_recalculate_invoice_settlement_balance
    ON tenant_data.invoice_settlements;
CREATE TRIGGER trg_recalculate_invoice_settlement_balance
    AFTER INSERT OR UPDATE OR DELETE
    ON tenant_data.invoice_settlements
    FOR EACH ROW
    EXECUTE FUNCTION tenant_data.recalculate_invoice_balance();
