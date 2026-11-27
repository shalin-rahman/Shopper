"""Static checks on migration 032 (tenant-qualified foreign keys) and its precheck."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4] / "database"
SQL = (ROOT / "migrations" / "032_tenant_fks.sql").read_text(encoding="utf-8")
PRECHECK = (ROOT / "checks" / "032_precheck.sql").read_text(encoding="utf-8")
FLAT = " ".join(SQL.split())

LINK = re.compile(r"\('(\w+)',\s*'(\w+)',\s*'(\w+)',\s*'([A-Z ]+)'\)")
LINKS = LINK.findall(SQL)

# Every one-column FK between tenant_data tables before 032, with its delete rule.
EXPECTED = {
    ("product_categories", "parent_id", "product_categories", "SET NULL"),
    ("products", "category_id", "product_categories", "SET NULL"),
    ("stock_transactions", "product_id", "products", "CASCADE"),
    ("stock_transactions", "branch_id", "branches", "NO ACTION"),
    ("invoices", "customer_id", "customers", "SET NULL"),
    ("invoice_lines", "invoice_id", "invoices", "CASCADE"),
    ("invoice_lines", "product_id", "products", "SET NULL"),
    ("payments", "invoice_id", "invoices", "SET NULL"),
    ("cost_layers", "product_id", "products", "CASCADE"),
    ("cost_layers", "transaction_id", "stock_transactions", "CASCADE"),
    ("purchase_orders", "supplier_id", "suppliers", "NO ACTION"),
    ("po_lines", "po_id", "purchase_orders", "CASCADE"),
    ("po_lines", "product_id", "products", "NO ACTION"),
    ("expenses", "category_id", "expense_categories", "NO ACTION"),
    ("expenses", "staff_id", "staff", "NO ACTION"),
    ("customer_collections", "customer_id", "customers", "NO ACTION"),
    ("customer_collections", "collected_by", "staff", "NO ACTION"),
    ("account_transfers", "from_account_id", "accounts", "NO ACTION"),
    ("account_transfers", "to_account_id", "accounts", "NO ACTION"),
    ("account_transfers", "staff_id", "staff", "NO ACTION"),
    ("credit_notes", "invoice_id", "invoices", "CASCADE"),
    ("debit_notes", "supplier_id", "suppliers", "NO ACTION"),
    ("debit_notes", "po_id", "purchase_orders", "NO ACTION"),
    ("supplier_payments", "supplier_id", "suppliers", "NO ACTION"),
    ("supplier_payments", "po_id", "purchase_orders", "NO ACTION"),
    ("credit_note_lines", "credit_note_id", "credit_notes", "CASCADE"),
    ("credit_note_lines", "invoice_id", "invoices", "CASCADE"),
    ("credit_note_lines", "invoice_line_id", "invoice_lines", "CASCADE"),
    ("credit_note_lines", "product_id", "products", "RESTRICT"),
    ("stock_levels", "branch_id", "branches", "NO ACTION"),
    ("stock_levels", "product_id", "products", "CASCADE"),
    ("staff", "branch_id", "branches", "NO ACTION"),
    ("payment_refunds", "payment_id", "payments", "NO ACTION"),
    ("payment_refunds", "invoice_id", "invoices", "NO ACTION"),
    ("payment_refunds", "credit_note_id", "credit_notes", "NO ACTION"),
}


def test_032_is_one_transaction():
    assert SQL.lstrip().splitlines()[0].startswith("--")
    assert "BEGIN;" in SQL and SQL.rstrip().endswith("COMMIT;")
    assert FLAT.count("BEGIN;") == 1 and FLAT.count("COMMIT;") == 1


def test_032_covers_every_link_once_with_its_old_delete_rule():
    assert len(LINKS) == len(set(LINKS)) == len(EXPECTED)
    assert set(LINKS) == EXPECTED


def test_032_set_null_keeps_tenant_id():
    # Without the column list, a parent delete would also null tenant_id (NOT NULL) and fail.
    assert "CASE WHEN r.on_delete = 'SET NULL' THEN format('SET NULL (%I)', r.col)" in FLAT
    assert "FOREIGN KEY (tenant_id, %I) ' 'REFERENCES tenant_data.%I (tenant_id, id)" in FLAT


def test_032_rerun_safe_fk_swap():
    assert "IF NOT EXISTS ( SELECT 1 FROM pg_index i" in FLAT
    assert "CREATE UNIQUE INDEX %I ON tenant_data.%I (tenant_id, id)" in FLAT
    assert "DROP CONSTRAINT %I" in FLAT
    assert "NOT VALID" in FLAT and "VALIDATE CONSTRAINT %I" in FLAT


def test_032_po_lines_get_tenant_id_and_policy():
    assert "ALTER TABLE tenant_data.po_lines ADD COLUMN IF NOT EXISTS tenant_id UUID;" in FLAT
    assert "WHERE po.id = l.po_id AND l.tenant_id IS NULL;" in FLAT
    assert (
        "ALTER TABLE tenant_data.po_lines ALTER COLUMN tenant_id SET DEFAULT tenant_data.app_tenant_id();"
    ) in FLAT
    assert "ALTER TABLE tenant_data.po_lines ALTER COLUMN tenant_id SET NOT NULL;" in FLAT
    assert "DROP POLICY IF EXISTS tenant_isolation_po_lines ON tenant_data.po_lines;" in FLAT
    assert (
        "CREATE POLICY tenant_isolation_po_lines ON tenant_data.po_lines FOR ALL TO shopper_app "
        "USING (tenant_id = tenant_data.app_tenant_id()) "
        "WITH CHECK (tenant_id = tenant_data.app_tenant_id());"
    ) in FLAT


def test_032_precheck_has_one_select_per_link():
    assert PRECHECK.count("UNION ALL") == len(EXPECTED) - 1
    names = set(re.findall(r"SELECT '(\w+\.\w+)'", PRECHECK))
    assert names == {f"{child}.{col}" for child, col, _, _ in EXPECTED}
