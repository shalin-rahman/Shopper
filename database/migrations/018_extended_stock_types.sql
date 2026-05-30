-- database/migrations/018_extended_stock_types.sql
-- Expands the stock transaction types for better tracking of gifts, damages, returns, etc.

ALTER TABLE tenant_data.stock_transactions DROP CONSTRAINT IF EXISTS stock_transactions_transaction_type_check;

ALTER TABLE tenant_data.stock_transactions ADD CONSTRAINT stock_transactions_transaction_type_check 
    CHECK (transaction_type IN (
        'in',           -- General increase
        'out',          -- General decrease
        'adjustment',   -- Correction
        'receive',      -- Stock in from supplier
        'return_in',    -- Customer return
        'gift_in',      -- Received as gift/bonus
        'damage',       -- Stock-out due to breakage
        'return_out',   -- Return to supplier
        'gift_out',     -- Given as marketing gift
        'expired'       -- Stock-out due to expiry
    ));

ALTER TABLE tenant_data.stock_transactions ADD COLUMN IF NOT EXISTS reason_code TEXT;
