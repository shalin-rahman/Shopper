-- database/migrations/021_chart_of_accounts.sql
-- Implements formal Chart of Accounts (COA) for total financial management.

CREATE TYPE tenant_data.account_type AS ENUM ('asset', 'liability', 'equity', 'revenue', 'expense');

CREATE TABLE IF NOT EXISTS tenant_data.accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_bn TEXT NOT NULL,
    account_type tenant_data.account_type NOT NULL,
    current_balance NUMERIC(18, 4) NOT NULL DEFAULT 0,
    is_system BOOLEAN NOT NULL DEFAULT false, -- True for Cash, Bank, AR, AP
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

-- Seed system accounts for every tenant
-- This will be handled by a function called during registration or migration.

CREATE OR REPLACE FUNCTION tenant_data.provision_system_accounts(tid UUID)
RETURNS void AS $$
BEGIN
    INSERT INTO tenant_data.accounts (tenant_id, code, name_en, name_bn, account_type, is_system)
    VALUES 
        (tid, '1000', 'Cash', 'নগদ', 'asset', true),
        (tid, '1001', 'Bank', 'ব্যাংক', 'asset', true),
        (tid, '1100', 'Accounts Receivable', 'পাওনা (AR)', 'asset', true),
        (tid, '2100', 'Accounts Payable', 'দেনা (AP)', 'liability', true),
        (tid, '3000', 'Equity', 'মূলধন', 'equity', true),
        (tid, '4000', 'Sales Revenue', 'বিক্রয় আয়', 'revenue', true),
        (tid, '5000', 'Cost of Goods Sold', 'বিক্রয় পণ্যের ব্যয়', 'expense', true)
    ON CONFLICT (tenant_id, code) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Apply to existing tenants
SELECT tenant_data.provision_system_accounts(id) FROM platform.tenants;

-- Account Transfers: Moving money between Cash/Bank etc.
CREATE TABLE IF NOT EXISTS tenant_data.account_transfers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    from_account_id UUID NOT NULL REFERENCES tenant_data.accounts (id),
    to_account_id UUID NOT NULL REFERENCES tenant_data.accounts (id),
    amount NUMERIC(18, 4) NOT NULL,
    description TEXT,
    staff_id UUID REFERENCES tenant_data.staff (id),
    transfer_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS & Grants
ALTER TABLE tenant_data.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.account_transfers ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_accounts ON tenant_data.accounts FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());
CREATE POLICY tenant_isolation_transfers ON tenant_data.account_transfers FOR ALL TO shopper_app USING (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE ON tenant_data.accounts TO shopper_app;
GRANT SELECT, INSERT ON tenant_data.account_transfers TO shopper_app;

-- Trigger to update account balances on ledger entry
CREATE OR REPLACE FUNCTION tenant_data.sync_account_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- This is a simplified version. In real ERP, total balance is derived from ledger.
    -- Here we update the account's current_balance field for performance.
    UPDATE tenant_data.accounts
    SET current_balance = current_balance + (COALESCE(NEW.debit, 0) - COALESCE(NEW.credit, 0))
    WHERE tenant_id = NEW.tenant_id AND code = NEW.account_code;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ledger_account_sync
    AFTER INSERT ON tenant_data.ledger_entries
    FOR EACH ROW
    EXECUTE PROCEDURE tenant_data.sync_account_balance();
