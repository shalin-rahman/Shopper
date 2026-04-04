-- Idempotent: safe via Docker init (02_apply_migrations.sh) and database/run_migrations.py.
-- Per-tenant branding, VAT defaults, modules (Mushak headers, storefront theme).

CREATE TABLE IF NOT EXISTS platform.tenant_settings (
    tenant_id UUID PRIMARY KEY REFERENCES platform.tenants (id) ON DELETE CASCADE,
    theme_id TEXT NOT NULL DEFAULT 'default',
    default_language TEXT NOT NULL DEFAULT 'en' CHECK (default_language IN ('en', 'bn')),
    logo_url TEXT,
    legal_title_en TEXT,
    legal_title_bn TEXT,
    bin TEXT,
    default_vat_rate_pct NUMERIC(5, 2) NOT NULL DEFAULT 0,
    module_access JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION platform.touch_tenant_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_tenant_settings_updated_at ON platform.tenant_settings;
CREATE TRIGGER trg_tenant_settings_updated_at
    BEFORE UPDATE ON platform.tenant_settings
    FOR EACH ROW
    EXECUTE PROCEDURE platform.touch_tenant_settings_updated_at();

ALTER TABLE platform.tenant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform.tenant_settings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_settings_select ON platform.tenant_settings;
CREATE POLICY tenant_settings_select
    ON platform.tenant_settings
    FOR SELECT
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id());

DROP POLICY IF EXISTS tenant_settings_update ON platform.tenant_settings;
CREATE POLICY tenant_settings_update
    ON platform.tenant_settings
    FOR UPDATE
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, UPDATE ON platform.tenant_settings TO shopper_app;
GRANT ALL ON platform.tenant_settings TO shopper_migrate;

INSERT INTO platform.tenant_settings (
    tenant_id,
    theme_id,
    default_language,
    legal_title_en,
    legal_title_bn,
    bin,
    default_vat_rate_pct,
    module_access
)
SELECT
    t.id,
    'default',
    'en',
    'Demo Traders Ltd.',
    'ডেমো ট্রেডার্স লিমিটেড',
    '000000000-0000',
    15,
    '{"products": true, "reports": false}'::jsonb
FROM platform.tenants t
WHERE t.subdomain = 'demo'
ON CONFLICT (tenant_id) DO NOTHING;
