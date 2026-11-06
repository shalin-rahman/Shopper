"""Static checks on migration 027 and the init script. The live DB checks are in tests/integration."""

import re
from pathlib import Path

DATABASE = Path(__file__).resolve().parents[4] / "database"
SQL = (DATABASE / "migrations" / "027_review_hardening.sql").read_text(encoding="utf-8")
INIT = DATABASE / "init" / "02_apply_migrations.sh"

UNFORCED_TABLES = (
    "suppliers",
    "purchase_orders",
    "po_lines",
    "expense_categories",
    "expenses",
    "customer_collections",
    "accounts",
    "account_transfers",
    "supplier_payments",
)


def test_027_forces_rls_on_all_listed_tables():
    for table in UNFORCED_TABLES:
        assert f"ALTER TABLE tenant_data.{table} FORCE ROW LEVEL SECURITY;" in SQL, table


def test_027_audit_chain_uses_lock_and_seq():
    assert "pg_advisory_xact_lock(hashtextextended(NEW.tenant_id::text, 0))" in SQL
    # The sequence value is taken after the lock, so chain order equals seq order.
    lock_at = SQL.index("pg_advisory_xact_lock")
    seq_at = SQL.index("NEW.chain_seq := nextval(")
    assert lock_at < seq_at
    assert "ORDER BY chain_seq DESC" in SQL
    assert "GRANT USAGE ON SEQUENCE tenant_data.audit_log_chain_seq TO shopper_app" in SQL


def test_027_payment_order_unique_index():
    assert re.search(
        r"CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_tenant_gateway_order\s+"
        r"ON tenant_data\.payments \(tenant_id, gateway, order_id\)\s+"
        r"WHERE order_id IS NOT NULL",
        SQL,
    )
    # Duplicates must stop the migration with a clear message, not a raw index error.
    assert "RAISE EXCEPTION" in SQL


def test_init_apply_script_records_versions():
    script = INIT.read_text(encoding="utf-8")
    assert script.strip(), "02_apply_migrations.sh is empty"
    assert "ON_ERROR_STOP=1" in script
    assert "platform.schema_migrations" in script
    assert "\r\n" not in script, "the postgres image runs this under sh; CRLF breaks it"
