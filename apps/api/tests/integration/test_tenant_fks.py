"""
Migration 032: foreign keys carry tenant_id, so a row cannot point at another tenant's row.
Same env as test_rls_isolation.py (INTEGRATION_TEST=1, MIGRATE_DATABASE_URL, DATABASE_URL).
"""

from __future__ import annotations

import asyncio
import uuid

import asyncpg
import pytest

from core.config import get_settings

pytestmark = pytest.mark.skipif(
    not get_settings().integration_test,
    reason="Set INTEGRATION_TEST=1, MIGRATE_DATABASE_URL and DATABASE_URL to run tenant FK checks",
)


def _migration_dsn() -> str:
    settings = get_settings()
    dsn = settings.migrate_database_url or settings.database_url
    if not dsn:
        pytest.skip("MIGRATE_DATABASE_URL or DATABASE_URL is required for integration tests")
    return settings.normalize_dsn(dsn)


def _application_dsn() -> str:
    settings = get_settings()
    if not settings.database_url:
        pytest.skip("DATABASE_URL for the shopper_app role is required for tenant FK checks")
    return settings.normalize_dsn(settings.database_url)


def _tag() -> str:
    return uuid.uuid4().hex[:8]


async def _seed_tenant(conn: asyncpg.Connection, label: str) -> dict:
    tenant = await conn.fetchval(
        """
        INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
        VALUES ($1, $2, $2, 'active') RETURNING id
        """,
        f"fk-{label}-{_tag()}",
        f"FK Tenant {label}",
    )
    category = await conn.fetchval(
        """
        INSERT INTO tenant_data.product_categories (tenant_id, name_en, name_bn, slug)
        VALUES ($1, 'Cat', 'Cat', $2) RETURNING id
        """,
        tenant,
        f"fk-{label}-{_tag()}",
    )
    product = await conn.fetchval(
        """
        INSERT INTO tenant_data.products (tenant_id, category_id, sku, name_en, name_bn, sell_price)
        VALUES ($1, $2, $3, 'P', 'P', 10) RETURNING id
        """,
        tenant,
        category,
        f"FK-{label}-{_tag()}",
    )
    expense_category = await conn.fetchval(
        """
        INSERT INTO tenant_data.expense_categories (tenant_id, name_en, name_bn)
        VALUES ($1, 'Rent', 'Rent') RETURNING id
        """,
        tenant,
    )
    branch = await conn.fetchval(
        """
        INSERT INTO tenant_data.branches (tenant_id, name, code, is_main)
        VALUES ($1, 'Main', $2, true) RETURNING id
        """,
        tenant,
        f"M{_tag()}",
    )
    invoice = await conn.fetchval(
        """
        INSERT INTO tenant_data.invoices (tenant_id, invoice_no, total_amount, balance_due)
        VALUES ($1, $2, 10, 10) RETURNING id
        """,
        tenant,
        f"FK-{label}-{_tag()}",
    )
    return {
        "tenant": tenant,
        "category": category,
        "product": product,
        "expense_category": expense_category,
        "branch": branch,
        "invoice": invoice,
    }


async def _seed(dsn: str) -> tuple[dict, dict]:
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            return await _seed_tenant(conn, "a"), await _seed_tenant(conn, "b")
    finally:
        await conn.close()


async def _cleanup(dsn: str, tenant_ids: list[uuid.UUID]) -> None:
    # Audited rows go first, while the tenant still exists (see test_rls_isolation.py).
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            for table in (
                "expenses",
                "expense_categories",
                "stock_levels",
                "invoice_lines",
                "payments",
                "invoices",
                "products",
                "product_categories",
                "branches",
                "audit_log",
            ):
                await conn.execute(
                    f"DELETE FROM tenant_data.{table} WHERE tenant_id = ANY($1::uuid[])",
                    tenant_ids,
                )
            await conn.execute("DELETE FROM platform.tenants WHERE id = ANY($1::uuid[])", tenant_ids)
    finally:
        await conn.close()


@pytest.fixture(scope="module")
def tenants():
    dsn = _migration_dsn()
    a, b = asyncio.run(_seed(dsn))
    try:
        yield a, b
    finally:
        asyncio.run(_cleanup(dsn, [a["tenant"], b["tenant"]]))


async def _insert_as_tenant(tenant_id: uuid.UUID, sql: str, *args) -> None:
    conn = await asyncpg.connect(_application_dsn())
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant_id))
            await conn.execute(sql, *args)
    finally:
        await conn.close()


def test_expense_cannot_use_another_tenants_category(tenants):
    a, b = tenants
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        asyncio.run(
            _insert_as_tenant(
                a["tenant"],
                "INSERT INTO tenant_data.expenses (tenant_id, category_id, amount) VALUES ($1, $2, 5)",
                a["tenant"],
                b["expense_category"],
            )
        )


def test_invoice_line_cannot_use_another_tenants_product(tenants):
    a, b = tenants
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        asyncio.run(
            _insert_as_tenant(
                a["tenant"],
                """
                INSERT INTO tenant_data.invoice_lines (tenant_id, invoice_id, product_id, description)
                VALUES ($1, $2, $3, 'cross')
                """,
                a["tenant"],
                a["invoice"],
                b["product"],
            )
        )


def test_stock_level_cannot_use_another_tenants_branch(tenants):
    a, b = tenants
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        asyncio.run(
            _insert_as_tenant(
                a["tenant"],
                """
                INSERT INTO tenant_data.stock_levels (tenant_id, branch_id, product_id, quantity)
                VALUES ($1, $2, $3, 0)
                """,
                a["tenant"],
                b["branch"],
                a["product"],
            )
        )


def test_own_tenant_links_still_work(tenants):
    a, _ = tenants
    asyncio.run(
        _insert_as_tenant(
            a["tenant"],
            "INSERT INTO tenant_data.expenses (tenant_id, category_id, amount) VALUES ($1, $2, 5)",
            a["tenant"],
            a["expense_category"],
        )
    )


async def _delete_category_keeps_product(tenant_id: uuid.UUID) -> asyncpg.Record:
    migrate = await asyncpg.connect(_migration_dsn())
    try:
        category = await migrate.fetchval(
            """
            INSERT INTO tenant_data.product_categories (tenant_id, name_en, name_bn, slug)
            VALUES ($1, 'Gone', 'Gone', $2) RETURNING id
            """,
            tenant_id,
            f"fk-gone-{_tag()}",
        )
        product = await migrate.fetchval(
            """
            INSERT INTO tenant_data.products (tenant_id, category_id, sku, name_en, name_bn, sell_price)
            VALUES ($1, $2, $3, 'P', 'P', 10) RETURNING id
            """,
            tenant_id,
            category,
            f"FK-GONE-{_tag()}",
        )
        await _insert_as_tenant(
            tenant_id, "DELETE FROM tenant_data.product_categories WHERE id = $1", category
        )
        return await migrate.fetchrow(
            "SELECT tenant_id, category_id FROM tenant_data.products WHERE id = $1", product
        )
    finally:
        await migrate.close()


def test_deleting_category_nulls_product_category_only(tenants):
    a, _ = tenants
    row = asyncio.run(_delete_category_keeps_product(a["tenant"]))
    assert row["category_id"] is None
    assert row["tenant_id"] == a["tenant"]


async def _delete_invoice(tenant_id: uuid.UUID) -> tuple[int, asyncpg.Record]:
    migrate = await asyncpg.connect(_migration_dsn())
    try:
        invoice = await migrate.fetchval(
            """
            INSERT INTO tenant_data.invoices (tenant_id, invoice_no, total_amount, balance_due)
            VALUES ($1, $2, 10, 10) RETURNING id
            """,
            tenant_id,
            f"FK-DEL-{_tag()}",
        )
        await migrate.execute(
            """
            INSERT INTO tenant_data.invoice_lines (tenant_id, invoice_id, description)
            VALUES ($1, $2, 'line')
            """,
            tenant_id,
            invoice,
        )
        payment = await migrate.fetchval(
            """
            INSERT INTO tenant_data.payments (tenant_id, invoice_id, gateway, amount)
            VALUES ($1, $2, 'bkash', 10) RETURNING id
            """,
            tenant_id,
            invoice,
        )
        await migrate.execute("DELETE FROM tenant_data.invoices WHERE id = $1", invoice)
        lines = await migrate.fetchval(
            "SELECT count(*) FROM tenant_data.invoice_lines WHERE invoice_id = $1", invoice
        )
        pay = await migrate.fetchrow(
            "SELECT tenant_id, invoice_id FROM tenant_data.payments WHERE id = $1", payment
        )
        return lines, pay
    finally:
        await migrate.close()


def test_deleting_invoice_cascades_lines_and_nulls_payment_invoice(tenants):
    a, _ = tenants
    lines, payment = asyncio.run(_delete_invoice(a["tenant"]))
    assert lines == 0
    assert payment["invoice_id"] is None
    assert payment["tenant_id"] == a["tenant"]
