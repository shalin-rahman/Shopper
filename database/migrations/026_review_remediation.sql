-- Align deployed schema and database constraints with the reviewed commerce behavior.
BEGIN;

ALTER TABLE tenant_data.products
    ADD COLUMN IF NOT EXISTS stock_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS marketplace_enabled BOOLEAN NOT NULL DEFAULT false;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tenant_data.products'::regclass
          AND conname = 'products_stock_quantity_nonnegative'
    ) THEN
        ALTER TABLE tenant_data.products
            ADD CONSTRAINT products_stock_quantity_nonnegative
            CHECK (stock_quantity >= 0);
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_categories_tenant_id_id
    ON tenant_data.product_categories (tenant_id, id);

-- Preserve products but clear invalid legacy cross-tenant category links before constraining them.
UPDATE tenant_data.products AS p
SET category_id = NULL
FROM tenant_data.product_categories AS c
WHERE p.category_id = c.id
  AND p.tenant_id <> c.tenant_id;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tenant_data.products'::regclass
          AND conname = 'products_category_tenant_fk'
    ) THEN
        ALTER TABLE tenant_data.products
            ADD CONSTRAINT products_category_tenant_fk
            FOREIGN KEY (tenant_id, category_id)
            REFERENCES tenant_data.product_categories (tenant_id, id);
    END IF;
END;
$$;

-- A finalized sale with no collection is an issued invoice, not a draft.
ALTER TABLE tenant_data.invoices
    DROP CONSTRAINT IF EXISTS invoices_status_check;
ALTER TABLE tenant_data.invoices
    ADD CONSTRAINT invoices_status_check
    CHECK (status IN ('draft', 'issued', 'partially_paid', 'paid', 'cancelled'));
ALTER TABLE tenant_data.invoices
    ADD COLUMN IF NOT EXISTS pos_tender TEXT;
ALTER TABLE tenant_data.invoices
    DROP CONSTRAINT IF EXISTS invoices_pos_tender_check;
ALTER TABLE tenant_data.invoices
    ADD CONSTRAINT invoices_pos_tender_check
    CHECK (
        pos_tender IS NULL
        OR pos_tender IN ('cash', 'bkash', 'nagad', 'rocket', 'bank', 'card', 'credit', 'other')
    );

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
            WHEN status = 'issued' THEN 'issued'
            ELSE 'draft'
        END,
        updated_at = now()
    WHERE id = p_invoice_id;
END;
$$ LANGUAGE plpgsql;

-- A narrow public function exposes only opted-in listing fields. Its fixed search_path
-- and result shape prevent the app role from receiving general cross-tenant table access.
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
      AND t.status = 'active'
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
