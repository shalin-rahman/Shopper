-- database/migrations/032_tenant_fks.sql
-- Foreign keys check tenant_id too, so a row can only point at a row of its own tenant
-- (FK checks bypass RLS). po_lines gets tenant_id. One FK per link; delete rules unchanged.
-- Run database/checks/032_precheck.sql first: every count must be 0.
-- Safe to rerun.

BEGIN;

ALTER TABLE tenant_data.po_lines ADD COLUMN IF NOT EXISTS tenant_id UUID;
UPDATE tenant_data.po_lines l SET tenant_id = po.tenant_id
  FROM tenant_data.purchase_orders po
 WHERE po.id = l.po_id AND l.tenant_id IS NULL;
ALTER TABLE tenant_data.po_lines ALTER COLUMN tenant_id SET DEFAULT tenant_data.app_tenant_id();
ALTER TABLE tenant_data.po_lines ALTER COLUMN tenant_id SET NOT NULL;
DROP POLICY IF EXISTS tenant_isolation_po_lines ON tenant_data.po_lines;
CREATE POLICY tenant_isolation_po_lines ON tenant_data.po_lines FOR ALL TO shopper_app
  USING (tenant_id = tenant_data.app_tenant_id())
  WITH CHECK (tenant_id = tenant_data.app_tenant_id());

DO $$
DECLARE
  r record;
  c record;
  fk text;
BEGIN
  FOR r IN SELECT * FROM (VALUES
    ('product_categories',  'parent_id',       'product_categories', 'SET NULL'),
    ('products',            'category_id',     'product_categories', 'SET NULL'),
    ('stock_transactions',  'product_id',      'products',           'CASCADE'),
    ('stock_transactions',  'branch_id',       'branches',           'NO ACTION'),
    ('invoices',            'customer_id',     'customers',          'SET NULL'),
    ('invoice_lines',       'invoice_id',      'invoices',           'CASCADE'),
    ('invoice_lines',       'product_id',      'products',           'SET NULL'),
    ('payments',            'invoice_id',      'invoices',           'SET NULL'),
    ('cost_layers',         'product_id',      'products',           'CASCADE'),
    ('cost_layers',         'transaction_id',  'stock_transactions', 'CASCADE'),
    ('purchase_orders',     'supplier_id',     'suppliers',          'NO ACTION'),
    ('po_lines',            'po_id',           'purchase_orders',    'CASCADE'),
    ('po_lines',            'product_id',      'products',           'NO ACTION'),
    ('expenses',            'category_id',     'expense_categories', 'NO ACTION'),
    ('expenses',            'staff_id',        'staff',              'NO ACTION'),
    ('customer_collections','customer_id',     'customers',          'NO ACTION'),
    ('customer_collections','collected_by',    'staff',              'NO ACTION'),
    ('account_transfers',   'from_account_id', 'accounts',           'NO ACTION'),
    ('account_transfers',   'to_account_id',   'accounts',           'NO ACTION'),
    ('account_transfers',   'staff_id',        'staff',              'NO ACTION'),
    ('credit_notes',        'invoice_id',      'invoices',           'CASCADE'),
    ('debit_notes',         'supplier_id',     'suppliers',          'NO ACTION'),
    ('debit_notes',         'po_id',           'purchase_orders',    'NO ACTION'),
    ('supplier_payments',   'supplier_id',     'suppliers',          'NO ACTION'),
    ('supplier_payments',   'po_id',           'purchase_orders',    'NO ACTION'),
    ('credit_note_lines',   'credit_note_id',  'credit_notes',       'CASCADE'),
    ('credit_note_lines',   'invoice_id',      'invoices',           'CASCADE'),
    ('credit_note_lines',   'invoice_line_id', 'invoice_lines',      'CASCADE'),
    ('credit_note_lines',   'product_id',      'products',           'RESTRICT'),
    ('stock_levels',        'branch_id',       'branches',           'NO ACTION'),
    ('stock_levels',        'product_id',      'products',           'CASCADE'),
    ('staff',               'branch_id',       'branches',           'NO ACTION'),
    ('payment_refunds',     'payment_id',      'payments',           'NO ACTION'),
    ('payment_refunds',     'invoice_id',      'invoices',           'NO ACTION'),
    ('payment_refunds',     'credit_note_id',  'credit_notes',       'NO ACTION')
  ) AS t(child, col, parent, on_delete)
  LOOP
    -- The parent needs a unique key on (tenant_id, id).
    IF NOT EXISTS (
      SELECT 1 FROM pg_index i
       WHERE i.indrelid = format('tenant_data.%I', r.parent)::regclass
         AND i.indisunique
         AND pg_get_indexdef(i.indexrelid) LIKE '%(tenant_id, id)'
    ) THEN
      EXECUTE format('CREATE UNIQUE INDEX %I ON tenant_data.%I (tenant_id, id)',
                     'uq_' || r.parent || '_tenant_id_id', r.parent);
    END IF;

    -- Drop every FK on this column (the old one-column FK, or an earlier tenant FK).
    FOR c IN
      SELECT con.conname
        FROM pg_constraint con
        JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey)
       WHERE con.conrelid = format('tenant_data.%I', r.child)::regclass
         AND con.contype = 'f'
         AND a.attname = r.col
    LOOP
      EXECUTE format('ALTER TABLE tenant_data.%I DROP CONSTRAINT %I', r.child, c.conname);
    END LOOP;

    fk := r.child || '_' || r.col || '_tfk';
    EXECUTE format(
      'ALTER TABLE tenant_data.%I ADD CONSTRAINT %I FOREIGN KEY (tenant_id, %I) '
      'REFERENCES tenant_data.%I (tenant_id, id) ON DELETE %s NOT VALID',
      r.child, fk, r.col, r.parent,
      CASE WHEN r.on_delete = 'SET NULL' THEN format('SET NULL (%I)', r.col) ELSE r.on_delete END);
    EXECUTE format('ALTER TABLE tenant_data.%I VALIDATE CONSTRAINT %I', r.child, fk);
  END LOOP;
END $$;

COMMIT;
