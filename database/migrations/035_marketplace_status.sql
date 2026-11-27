-- Marketplace search lists every shop that can sell: active, trialing and past_due,
-- the same set login allows (TRANSACTING_TENANT_STATUSES in core/tenant_context.py).
BEGIN;

CREATE OR REPLACE FUNCTION platform.search_public_marketplace_products(p_pattern TEXT)
RETURNS TABLE (
    id UUID,
    sku TEXT,
    name_en TEXT,
    name_bn TEXT,
    description_en TEXT,
    description_bn TEXT,
    unit TEXT,
    sell_price NUMERIC,
    mrp NUMERIC,
    vat_rate_pct NUMERIC,
    tenant_subdomain TEXT
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, platform, tenant_data
AS $$
    SELECT
        p.id,
        p.sku,
        p.name_en,
        p.name_bn,
        p.description_en,
        p.description_bn,
        p.unit,
        p.sell_price,
        p.mrp,
        p.vat_rate_pct,
        t.subdomain::text
    FROM tenant_data.products AS p
    JOIN platform.tenants AS t ON t.id = p.tenant_id
    WHERE p.marketplace_enabled = true
      AND p.is_active = true
      AND t.status IN ('active', 'trialing', 'past_due')
      AND (
          p_pattern IS NULL
          OR p.sku ILIKE p_pattern
          OR p.name_en ILIKE p_pattern
          OR p.name_bn ILIKE p_pattern
      )
$$;

ALTER FUNCTION platform.search_public_marketplace_products(TEXT) OWNER TO shopper_migrate;
REVOKE ALL ON FUNCTION platform.search_public_marketplace_products(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.search_public_marketplace_products(TEXT) TO shopper_app;
COMMIT;
