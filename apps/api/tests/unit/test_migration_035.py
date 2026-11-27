"""Static checks on migration 035 (marketplace search lists trialing and past_due shops)."""

from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[4] / "database" / "migrations"
SQL = (MIGRATIONS / "035_marketplace_status.sql").read_text(encoding="utf-8")
FLAT = " ".join(SQL.split())
FN = "platform.search_public_marketplace_products(TEXT)"


def test_035_is_one_transaction():
    assert "BEGIN;" in SQL and SQL.rstrip().endswith("COMMIT;")
    assert FLAT.count("BEGIN;") == 1 and FLAT.count("COMMIT;") == 1


def test_035_lists_every_transacting_status():
    assert "AND t.status IN ('active', 'trialing', 'past_due')" in FLAT
    assert "t.status = 'active'" not in FLAT


def test_035_keeps_function_security_and_grants():
    assert "CREATE OR REPLACE FUNCTION platform.search_public_marketplace_products(p_pattern TEXT)" in FLAT
    assert "SECURITY DEFINER SET search_path = pg_catalog, platform, tenant_data" in FLAT
    assert f"ALTER FUNCTION {FN} OWNER TO shopper_migrate;" in FLAT
    assert f"REVOKE ALL ON FUNCTION {FN} FROM PUBLIC;" in FLAT
    assert f"GRANT EXECUTE ON FUNCTION {FN} TO shopper_app;" in FLAT


def test_035_keeps_026_result_shape_and_filters():
    old = " ".join((MIGRATIONS / "026_review_remediation.sql").read_text(encoding="utf-8").split())

    def returns(text: str) -> str:
        start = text.index("RETURNS TABLE", text.index("search_public_marketplace_products(p_pattern TEXT)"))
        return text[start:text.index(")", text.index("tenant_subdomain TEXT", start)) + 1]

    assert returns(FLAT) == returns(old)
    assert "WHERE p.marketplace_enabled = true AND p.is_active = true" in FLAT
