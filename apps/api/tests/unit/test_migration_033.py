"""Static checks on migration 033 (cost layer added after the stock transaction row exists)."""

from pathlib import Path

SQL = (
    Path(__file__).resolve().parents[4] / "database" / "migrations" / "033_cost_layer_after_insert.sql"
).read_text(encoding="utf-8")
FLAT = " ".join(SQL.split())


def _body(name: str) -> str:
    start = FLAT.index(f"CREATE OR REPLACE FUNCTION tenant_data.{name}()")
    return FLAT[start:FLAT.index("$$ LANGUAGE plpgsql;", start)]


def test_033_is_one_transaction():
    assert "BEGIN;" in SQL and SQL.rstrip().endswith("COMMIT;")
    assert FLAT.count("BEGIN;") == 1 and FLAT.count("COMMIT;") == 1


def test_033_in_movements_add_cost_layer_after_insert():
    assert (
        "CREATE TRIGGER trg_add_cost_layer AFTER INSERT ON tenant_data.stock_transactions "
        "FOR EACH ROW WHEN (NEW.transaction_type = 'in') EXECUTE FUNCTION tenant_data.add_cost_layer();"
    ) in FLAT
    body = _body("add_cost_layer")
    assert "INSERT INTO tenant_data.cost_layers" in body
    assert "UPDATE tenant_data.products SET wac_cost" in body
    assert "RETURN NULL;" in body


def test_033_out_movements_stay_before_insert_and_skip_cost_layer_insert():
    assert (
        "CREATE TRIGGER trg_process_inventory_valuation BEFORE INSERT ON tenant_data.stock_transactions "
        "FOR EACH ROW WHEN (NEW.transaction_type = 'out')"
    ) in FLAT
    body = _body("process_inventory_valuation")
    assert "NEW.unit_cost :=" in body
    assert "INSERT INTO tenant_data.cost_layers" not in body
    assert "transaction_type = 'in'" not in body
    assert "UPDATE tenant_data.products" not in body


def test_033_backfills_layers_only_for_stock_without_layers():
    assert "ALTER TABLE tenant_data.cost_layers ALTER COLUMN transaction_id DROP NOT NULL;" in FLAT
    backfill = FLAT[FLAT.index("INSERT INTO tenant_data.cost_layers", FLAT.index("DROP NOT NULL")):]
    assert "COALESCE(NULLIF(p.wac_cost, 0), p.buy_price, 0)" in backfill
    assert "WHERE p.stock_quantity > 0" in backfill
    assert "AND NOT EXISTS ( SELECT 1 FROM tenant_data.cost_layers c" in backfill
    assert backfill.index("NOT EXISTS") < backfill.index("COMMIT;")


def test_033_rerun_safe():
    assert "DROP TRIGGER IF EXISTS trg_process_inventory_valuation" in FLAT
    assert "DROP TRIGGER IF EXISTS trg_add_cost_layer" in FLAT
    assert FLAT.count("CREATE OR REPLACE FUNCTION") == 2
