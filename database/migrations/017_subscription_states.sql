-- database/migrations/017_subscription_states.sql
-- Expands the tenant lifecycle status to support the Dunning State Machine (Phase 4).

-- 1. Create a temporary copy of the check constraint removal logic if needed, 
-- but in Postgres, we usually just drop and recreate the constraint.
ALTER TABLE platform.tenants DROP CONSTRAINT IF EXISTS tenants_status_check;

-- 2. Apply the new expanded constraint
ALTER TABLE platform.tenants ADD CONSTRAINT tenants_status_check 
    CHECK (status IN (
        'trialing',   -- Initial period
        'active',     -- Subscribed & paid
        'past_due',   -- Payment failed, in dunning
        'suspended',  -- Access blocked after grace period
        'canceled',   -- Explicitly terminated
        'deleted',    -- Scheduled for purge
        'pending'     -- Initial provisioning state
    ));

-- 3. Add subscription metadata for dunning logic
ALTER TABLE platform.tenants ADD COLUMN IF NOT EXISTS subscription_plan TEXT DEFAULT 'free';
ALTER TABLE platform.tenants ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ;
ALTER TABLE platform.tenants ADD COLUMN IF NOT EXISTS last_payment_failed_at TIMESTAMPTZ;
ALTER TABLE platform.tenants ADD COLUMN IF NOT EXISTS dunning_notified_count INT DEFAULT 0;
