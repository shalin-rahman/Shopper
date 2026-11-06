"""Static checks on migration 031 (leftovers: debit notes, staff branch, audit noise, refunds)."""

import re
from pathlib import Path

SQL = (
    Path(__file__).resolve().parents[4] / "database" / "migrations" / "031_leftovers.sql"
).read_text(encoding="utf-8")

FLAT = " ".join(SQL.split())


def _statement(start: str) -> str:
    part = FLAT[FLAT.index(start):]
    return part[:part.index(";")]


def test_031_is_one_transaction():
    assert SQL.lstrip().splitlines()[0].startswith("--")
    assert "BEGIN;" in SQL and SQL.rstrip().endswith("COMMIT;")


def test_031_debit_notes_get_po_and_supplier():
    assert "ADD COLUMN IF NOT EXISTS po_id UUID REFERENCES tenant_data.purchase_orders (id)" in FLAT
    assert "ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES tenant_data.suppliers (id)" in FLAT
    for col in ("adjustment_amount_taxable", "adjustment_amount_vat", "total_adjustment"):
        assert f"ALTER COLUMN {col} SET DEFAULT 0" in FLAT, col


def test_031_debit_note_backfill_only_fills_blanks():
    backfill = _statement("UPDATE tenant_data.debit_notes")
    assert "FROM tenant_data.purchase_orders" in backfill
    assert "dn.po_id IS NULL" in backfill


def test_031_debit_notes_one_policy_with_check_and_no_delete():
    assert "DROP POLICY IF EXISTS tenant_isolation_debit_notes ON tenant_data.debit_notes;" in FLAT
    assert (
        "CREATE POLICY tenant_isolation_dn ON tenant_data.debit_notes FOR ALL TO shopper_app "
        "USING (tenant_id = tenant_data.app_tenant_id()) "
        "WITH CHECK (tenant_id = tenant_data.app_tenant_id());"
    ) in FLAT
    assert "REVOKE DELETE ON tenant_data.debit_notes FROM shopper_app;" in FLAT


def test_031_inventory_transfers_dropped_only_when_empty():
    assert "SET LOCAL row_security = off;" in FLAT
    block = FLAT[FLAT.index("inventory_transfers"):]
    assert "EXISTS (SELECT 1 FROM tenant_data.inventory_transfers)" in block
    assert "RAISE NOTICE" in block
    assert "DROP TABLE tenant_data.inventory_transfers;" in block


def test_031_staff_branch_is_optional():
    assert (
        "ALTER TABLE tenant_data.staff ADD COLUMN IF NOT EXISTS branch_id UUID "
        "REFERENCES tenant_data.branches (id);"
    ) in FLAT


def test_031_product_audit_skips_stock_only_updates():
    assert "DROP TRIGGER IF EXISTS trg_audit_products ON tenant_data.products;" in FLAT
    assert re.search(
        r"CREATE TRIGGER trg_audit_products AFTER INSERT OR DELETE ON tenant_data\.products",
        FLAT,
    )
    update = _statement("CREATE TRIGGER trg_audit_products_update")
    assert "AFTER UPDATE ON tenant_data.products" in update
    assert (
        "WHEN ((to_jsonb(OLD) - 'stock_quantity') IS DISTINCT FROM (to_jsonb(NEW) - 'stock_quantity'))"
    ) in update
    assert "tenant_data.audit_row_change_fn()" in update


def test_031_refund_table_shape_and_rls():
    table = _statement("CREATE TABLE IF NOT EXISTS tenant_data.payment_refunds")
    assert "payment_id UUID NOT NULL REFERENCES tenant_data.payments (id)" in table
    assert "amount NUMERIC(18, 4) NOT NULL CHECK (amount > 0)" in table
    assert "credit_note_id UUID REFERENCES tenant_data.credit_notes (id)" in table
    assert "ALTER TABLE tenant_data.payment_refunds FORCE ROW LEVEL SECURITY;" in FLAT
    assert (
        "CREATE POLICY tenant_isolation_payment_refunds ON tenant_data.payment_refunds FOR ALL TO shopper_app "
        "USING (tenant_id = tenant_data.app_tenant_id()) "
        "WITH CHECK (tenant_id = tenant_data.app_tenant_id());"
    ) in FLAT
    # Refunds are a record of money sent back. They are never edited or removed.
    assert "GRANT SELECT, INSERT ON tenant_data.payment_refunds TO shopper_app;" in FLAT
    assert "GRANT ALL ON tenant_data.payment_refunds TO shopper_migrate;" in FLAT
    assert "trg_audit_payment_refunds" in FLAT


def test_031_balance_subtracts_refunds():
    fn = FLAT[FLAT.index("CREATE OR REPLACE FUNCTION tenant_data.refresh_invoice_balance"):]
    fn = fn[:fn.index("$$ LANGUAGE plpgsql")]
    assert "FROM tenant_data.payment_refunds" in fn
    assert "status = 'completed'" in fn
    trigger = _statement("CREATE TRIGGER trg_recalculate_invoice_refund_balance")
    assert "ON tenant_data.payment_refunds" in trigger
    assert "tenant_data.recalculate_invoice_balance()" in trigger


def test_031_refunded_invoice_never_falls_back_to_draft():
    fn = FLAT[FLAT.index("CREATE OR REPLACE FUNCTION tenant_data.refresh_invoice_balance"):]
    fn = fn[:fn.index("$$ LANGUAGE plpgsql")]
    assert "WHEN status = 'draft' THEN 'draft'" in fn
    assert "ELSE 'issued'" in fn


def test_031_balance_counts_refunds_of_completed_payments_only():
    fn = FLAT[FLAT.index("CREATE OR REPLACE FUNCTION tenant_data.refresh_invoice_balance"):]
    refunds = fn[fn.index("FROM tenant_data.payment_refunds"):]
    refunds = refunds[:refunds.index("), 0)")]
    assert "JOIN tenant_data.payments p ON p.id = r.payment_id" in refunds
    assert "p.status = 'completed'" in refunds
