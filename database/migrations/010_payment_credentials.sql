-- database/migrations/010_payment_credentials.sql
-- Adds tenant-specific payment gateway credentials to the settings table.
-- Each business profile manages its own credentials as per requirements.

ALTER TABLE platform.tenant_settings 
ADD COLUMN IF NOT EXISTS sslcommerz_store_id TEXT,
ADD COLUMN IF NOT EXISTS sslcommerz_store_password TEXT,
ADD COLUMN IF NOT EXISTS bkash_app_key TEXT,
ADD COLUMN IF NOT EXISTS bkash_app_secret TEXT,
ADD COLUMN IF NOT EXISTS bkash_username TEXT,
ADD COLUMN IF NOT EXISTS bkash_password TEXT,
ADD COLUMN IF NOT EXISTS nagad_merchant_id TEXT,
ADD COLUMN IF NOT EXISTS nagad_public_key TEXT,
ADD COLUMN IF NOT EXISTS nagad_private_key TEXT;

-- Update the touch trigger is already there and will handle updated_at.
