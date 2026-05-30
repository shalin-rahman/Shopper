-- database/migrations/016_customer_tin_nid.sql
-- Adds TIN and NID fields to customers for High-Value Trigger (Mushak 6.10) compliance.

ALTER TABLE tenant_data.customers ADD COLUMN IF NOT EXISTS tin TEXT;
ALTER TABLE tenant_data.customers ADD COLUMN IF NOT EXISTS nid TEXT;
ALTER TABLE tenant_data.customers ADD COLUMN IF NOT EXISTS bin TEXT;

-- Index for faster lookup during Mushak 6.10 generation
CREATE INDEX IF NOT EXISTS idx_customers_tin ON tenant_data.customers (tin);
CREATE INDEX IF NOT EXISTS idx_customers_bin ON tenant_data.customers (bin);
