-- Keep gateway payments that need a person to look at them.
-- A payment can complete after its invoice was cancelled or fully paid. The money is
-- already taken, so the IPN records it and sets review_reason. A manager refunds it at
-- the gateway (outside this system) and then resolves the review with a note.
-- Safe to run more than once.

BEGIN;

ALTER TABLE tenant_data.payments
    ADD COLUMN IF NOT EXISTS review_reason TEXT,
    ADD COLUMN IF NOT EXISTS review_note TEXT,
    ADD COLUMN IF NOT EXISTS review_resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS review_resolved_by TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tenant_data.payments'::regclass
          AND conname = 'payments_review_reason_check'
    ) THEN
        ALTER TABLE tenant_data.payments
            ADD CONSTRAINT payments_review_reason_check
            CHECK (review_reason IN ('invoice_cancelled', 'overpayment'));
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_payments_open_review
    ON tenant_data.payments (tenant_id)
    WHERE review_reason IS NOT NULL AND review_resolved_at IS NULL;

COMMIT;
