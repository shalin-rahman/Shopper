"""Static checks on migration 019 (suppliers and purchase orders)."""

from pathlib import Path

SQL = (
    Path(__file__).resolve().parents[4] / "database" / "migrations" / "019_suppliers_po.sql"
).read_text(encoding="utf-8")

FLAT = " ".join(SQL.split())


def _po_lines_policy() -> str:
    part = FLAT[FLAT.index("CREATE POLICY tenant_isolation_po_lines"):]
    return part[:part.index(";")]


def test_019_po_lines_policy_checks_tenant_through_its_po():
    # po_lines has no tenant_id column, so the policy must reach the tenant through the PO.
    policy = _po_lines_policy()
    assert "po.id = po_lines.po_id" in policy
    assert "po.tenant_id = tenant_data.app_tenant_id()" in policy
    assert "USING (tenant_id" not in policy


def test_019_policies_can_be_rerun():
    # An old failed run left the first two policies behind, so a rerun must drop them first.
    for name, table in [
        ("tenant_isolation_suppliers", "suppliers"),
        ("tenant_isolation_po", "purchase_orders"),
        ("tenant_isolation_po_lines", "po_lines"),
    ]:
        drop = f"DROP POLICY IF EXISTS {name} ON tenant_data.{table};"
        assert drop in FLAT
        assert FLAT.index(drop) < FLAT.index(f"CREATE POLICY {name} ")
