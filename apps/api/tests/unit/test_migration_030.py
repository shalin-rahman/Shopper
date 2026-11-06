"""Static checks on migration 030 (per-branch stock). No test runs 030 against a real database yet."""

import re
from pathlib import Path

SQL = (
    Path(__file__).resolve().parents[4] / "database" / "migrations" / "030_branch_stock.sql"
).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


FLAT = _flat(SQL)


def test_030_is_one_transaction():
    assert SQL.lstrip().splitlines()[0].startswith("--")
    assert "BEGIN;" in SQL and SQL.rstrip().endswith("COMMIT;")


def test_030_main_branch_insert_is_guarded():
    insert = FLAT[FLAT.index("INSERT INTO tenant_data.branches"):]
    insert = insert[:insert.index(";")]
    assert "'MAIN'" in insert
    assert "WHERE NOT EXISTS" in insert and "is_main" in insert


def test_030_only_one_main_branch_per_tenant():
    assert re.search(
        r"CREATE UNIQUE INDEX IF NOT EXISTS \w+ ON tenant_data\.branches \(tenant_id\) WHERE is_main",
        FLAT,
    )
    assert "UNIQUE (tenant_id, code)" in FLAT


def test_030_stock_backfill_does_not_double_on_rerun():
    insert = FLAT[FLAT.index("INSERT INTO tenant_data.stock_levels"):]
    insert = insert[:insert.index(";")]
    assert "ON CONFLICT (branch_id, product_id) DO NOTHING" in insert


def test_030_stock_levels_shape():
    assert "quantity NUMERIC(18, 4) NOT NULL DEFAULT 0 CHECK (quantity >= 0)" in FLAT
    assert "PRIMARY KEY (branch_id, product_id)" in FLAT


def test_030_rls_on_both_tables():
    for table in ("branches", "stock_levels"):
        assert f"ALTER TABLE tenant_data.{table} ENABLE ROW LEVEL SECURITY;" in FLAT, table
        assert f"ALTER TABLE tenant_data.{table} FORCE ROW LEVEL SECURITY;" in FLAT, table
        assert f"DROP POLICY IF EXISTS tenant_isolation_{table} ON tenant_data.{table};" in FLAT, table
        assert (
            f"CREATE POLICY tenant_isolation_{table} ON tenant_data.{table} FOR ALL TO shopper_app "
            "USING (tenant_id = tenant_data.app_tenant_id()) "
            "WITH CHECK (tenant_id = tenant_data.app_tenant_id());"
        ) in FLAT, table
        assert f"GRANT ALL ON tenant_data.{table} TO shopper_migrate;" in FLAT, table


def test_030_type_check_keeps_old_types_and_adds_transfers():
    check = re.search(r"stock_transactions_transaction_type_check CHECK \(transaction_type IN \(([^)]*)\)\)", FLAT)
    assert check
    types = set(re.findall(r"'(\w+)'", check.group(1)))
    old = {"in", "out", "adjustment", "receive", "return_in", "gift_in",
           "damage", "return_out", "gift_out", "expired"}
    assert types == old | {"transfer_out", "transfer_in"}
    assert "DROP CONSTRAINT IF EXISTS stock_transactions_transaction_type_check" in FLAT


def test_030_backfills_transaction_branch():
    assert "ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES tenant_data.branches (id)" in FLAT
    assert re.search(r"UPDATE tenant_data\.stock_transactions \w+ SET branch_id = [^;]* WHERE [^;]*\w+\.branch_id IS NULL;", FLAT)


def test_030_trigger_keeps_product_total_in_step():
    assert "DROP TRIGGER IF EXISTS trg_sync_product_stock ON tenant_data.stock_levels;" in FLAT
    assert "AFTER INSERT OR UPDATE OR DELETE ON tenant_data.stock_levels" in FLAT
    assert "SET stock_quantity = (SELECT COALESCE(SUM(quantity), 0)" in FLAT


def test_030_backfill_does_not_write_an_audit_row_per_old_transaction():
    disable = FLAT.index("ALTER TABLE tenant_data.stock_transactions DISABLE TRIGGER trg_audit_stock_transactions;")
    backfill = FLAT.index("UPDATE tenant_data.stock_transactions st SET branch_id")
    enable = FLAT.index("ALTER TABLE tenant_data.stock_transactions ENABLE TRIGGER trg_audit_stock_transactions;")
    assert disable < backfill < enable


def test_030_reconciles_product_totals_after_the_trigger_exists():
    # On a rerun the backfill skips existing rows, so totals that drifted are fixed here.
    trigger = FLAT.index("CREATE TRIGGER trg_sync_product_stock")
    reconcile = re.search(
        r"UPDATE tenant_data\.products p SET stock_quantity = s\.total FROM \(SELECT product_id, SUM\(quantity\) AS total "
        r"FROM tenant_data\.stock_levels GROUP BY product_id\) s WHERE s\.product_id = p\.id "
        r"AND p\.stock_quantity IS DISTINCT FROM s\.total;",
        FLAT,
    )
    assert reconcile and reconcile.start() > trigger
