"""
Run against a real Postgres with schema loaded and tenant fixtures created via a migrate-capable role:
  set INTEGRATION_TEST=1 SHOPPER_MIGRATE_DATABASE_URL=postgresql+asyncpg://shopper_migrate:...@host:5432/shopper
  pytest apps/api/tests/test_integration_rls.py -q
"""

# RLS assertions connect as shopper_app; fixture setup uses the migration URL.
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from importlib import reload

import asyncpg
import jwt
import pytest

from core.config import clear_settings_cache, get_settings

pytestmark = pytest.mark.skipif(
    not get_settings().integration_test,
    reason="Set INTEGRATION_TEST=1 and SHOPPER_MIGRATE_DATABASE_URL or DATABASE_URL to run RLS integration checks",
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
        pytest.skip("DATABASE_URL for the shopper_app role is required for RLS checks")
    return settings.normalize_dsn(settings.database_url)


async def _seed_tenant_data(
    dsn: str,
) -> tuple[str, str, uuid.UUID, uuid.UUID, str, str, uuid.UUID, uuid.UUID, uuid.UUID]:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    async with pool.acquire() as conn:
        async with conn.transaction():
            sub_a = f"integration-a-{uuid.uuid4().hex[:8]}"
            sub_b = f"integration-b-{uuid.uuid4().hex[:8]}"
            tenant_a = await conn.fetchval(
                """
                INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
                VALUES ($1, $2, $3, 'active')
                ON CONFLICT (subdomain) DO UPDATE SET status = 'active'
                RETURNING id
                """,
                sub_a,
                "Integration Tenant A",
                "ইন্টিগ্রেশন টেন্যান্ট এ",
            )
            tenant_b = await conn.fetchval(
                """
                INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
                VALUES ($1, $2, $3, 'active')
                ON CONFLICT (subdomain) DO UPDATE SET status = 'active'
                RETURNING id
                """,
                sub_b,
                "Integration Tenant B",
                "ইন্টিগ্রেশন টেন্যান্ট বি",
            )
            category_a = await conn.fetchval(
                """
                INSERT INTO tenant_data.product_categories (tenant_id, name_en, name_bn, slug)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                tenant_a,
                "Category A",
                "ক্যাটাগরি এ",
                f"int-a-{uuid.uuid4().hex[:8]}",
            )
            category_b = await conn.fetchval(
                """
                INSERT INTO tenant_data.product_categories (tenant_id, name_en, name_bn, slug)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                tenant_b,
                "Category B",
                "ক্যাটাগরি বি",
                f"int-b-{uuid.uuid4().hex[:8]}",
            )
            sku_a = f"INT-A-{uuid.uuid4().hex[:10]}"
            sku_b = f"INT-B-{uuid.uuid4().hex[:10]}"
            product_a = await conn.fetchval(
                """
                INSERT INTO tenant_data.products (
                    tenant_id, category_id, sku, name_en, name_bn, sell_price, vat_rate_pct,
                    is_active, marketplace_enabled
                ) VALUES ($1, $2, $3, $4, $5, 100.00, 15, true, true)
                ON CONFLICT (tenant_id, sku) DO UPDATE SET name_en = EXCLUDED.name_en
                RETURNING id
                """,
                tenant_a,
                category_a,
                sku_a,
                "Product A",
                "পণ্য এ",
            )
            product_b = await conn.fetchval(
                """
                INSERT INTO tenant_data.products (
                    tenant_id, category_id, sku, name_en, name_bn, sell_price, vat_rate_pct,
                    is_active, marketplace_enabled
                ) VALUES ($1, $2, $3, $4, $5, 120.00, 15, true, false)
                ON CONFLICT (tenant_id, sku) DO UPDATE SET name_en = EXCLUDED.name_en
                RETURNING id
                """,
                tenant_b,
                category_b,
                sku_b,
                "Product B",
                "পণ্য বি",
            )
            invoice_a = await conn.fetchval(
                """
                INSERT INTO tenant_data.invoices (
                    tenant_id, invoice_no, total_amount, balance_due
                ) VALUES ($1, $2, 100, 100)
                RETURNING id
                """,
                tenant_a,
                f"INT-A-{uuid.uuid4().hex[:10]}",
            )
            settlement_id = await conn.fetchval(
                """
                INSERT INTO tenant_data.invoice_settlements (
                    tenant_id, invoice_id, amount, payment_method, source, source_reference
                ) VALUES ($1, $2, 10, 'cash', 'pos', $3)
                RETURNING id
                """,
                tenant_a,
                invoice_a,
                str(uuid.uuid4()),
            )
    await pool.close()
    return (
        sub_a,
        sub_b,
        tenant_a,
        tenant_b,
        sku_a,
        sku_b,
        settlement_id,
        invoice_a,
        category_b,
    )


async def _cleanup_tenant_data(dsn: str, tenant_ids: list[uuid.UUID]) -> None:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM platform.tenants WHERE id = ANY($1::uuid[])",
                tenant_ids,
            )
    await pool.close()


@pytest.fixture(scope="module")
def seeded_tenants():
    dsn = _migration_dsn()
    (
        sub_a,
        sub_b,
        tenant_a,
        tenant_b,
        sku_a,
        sku_b,
        settlement_id,
        invoice_a,
        category_b,
    ) = asyncio.run(_seed_tenant_data(dsn))
    yield {
        "sub_a": sub_a,
        "sub_b": sub_b,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "sku_a": sku_a,
        "sku_b": sku_b,
        "settlement_id": settlement_id,
        "invoice_a": invoice_a,
        "category_b": category_b,
    }
    asyncio.run(_cleanup_tenant_data(dsn, [tenant_a, tenant_b]))


@pytest.fixture(scope="module")
def client():
    os.environ.pop("TESTING", None)
    from importlib import reload

    import main

    reload(main)
    from starlette.testclient import TestClient

    with TestClient(main.app) as c:
        yield c


def _tenant_auth_headers(subdomain: str, tenant_id: uuid.UUID) -> dict[str, str]:
    settings = get_settings()
    token = jwt.encode(
        {
            "uid": str(uuid.uuid4()),
            "tid": str(tenant_id),
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {
        "X-Shopper-Tenant": subdomain,
        "Authorization": f"Bearer {token}",
    }


def test_tenant_a_cannot_see_tenant_b_products(client, seeded_tenants):
    r = client.get(
        "/v1/tenant/products",
        headers=_tenant_auth_headers(seeded_tenants["sub_a"], seeded_tenants["tenant_a"]),
    )
    assert r.status_code == 200, r.text
    skus = {item["sku"] for item in r.json()}
    assert seeded_tenants["sku_a"] in skus
    assert seeded_tenants["sku_b"] not in skus

    r = client.get(
        "/v1/tenant/products",
        headers=_tenant_auth_headers(seeded_tenants["sub_b"], seeded_tenants["tenant_b"]),
    )
    assert r.status_code == 200, r.text
    skus = {item["sku"] for item in r.json()}
    assert seeded_tenants["sku_b"] in skus
    assert seeded_tenants["sku_a"] not in skus


def test_tenant_product_fetch_isolation(client, seeded_tenants):
    r = client.get(
        f"/v1/tenant/products/{seeded_tenants['tenant_a']}",
        headers=_tenant_auth_headers(seeded_tenants["sub_b"], seeded_tenants["tenant_b"]),
    )
    assert r.status_code == 404


async def _settlement_visible_to_tenant(
    dsn: str,
    tenant_id: uuid.UUID,
    settlement_id: uuid.UUID,
) -> bool:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('app.tenant_id', $1, true)",
                    str(tenant_id),
                )
                return bool(
                    await conn.fetchval(
                        "SELECT EXISTS (SELECT 1 FROM tenant_data.invoice_settlements WHERE id = $1)",
                        settlement_id,
                    )
                )
    finally:
        await pool.close()


def test_invoice_settlement_rows_are_tenant_isolated(seeded_tenants):
    dsn = _application_dsn()
    settlement_id = seeded_tenants["settlement_id"]
    tenant_a = seeded_tenants["tenant_a"]
    tenant_b = seeded_tenants["tenant_b"]

    assert asyncio.run(
        _settlement_visible_to_tenant(dsn, tenant_a, settlement_id)
    )
    assert not asyncio.run(
        _settlement_visible_to_tenant(dsn, tenant_b, settlement_id)
    )


async def _cross_tenant_invoice_reference_rejected(
    dsn: str,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> bool:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('app.tenant_id', $1, true)",
                    str(tenant_id),
                )
                try:
                    async with conn.transaction():
                        await conn.execute(
                            """
                            INSERT INTO tenant_data.invoice_settlements (
                                tenant_id, invoice_id, amount, payment_method, source, source_reference
                            ) VALUES ($1, $2, 1, 'cash', 'pos', $3)
                            """,
                            tenant_id,
                            invoice_id,
                            str(uuid.uuid4()),
                        )
                except asyncpg.ForeignKeyViolationError:
                    return True
                return False
    finally:
        await pool.close()


def test_invoice_settlement_cannot_reference_another_tenants_invoice(seeded_tenants):
    assert asyncio.run(
        _cross_tenant_invoice_reference_rejected(
            _application_dsn(),
            seeded_tenants["tenant_b"],
            seeded_tenants["invoice_a"],
        )
    )


async def _public_marketplace_skus(dsn: str) -> set[str]:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sku
                FROM platform.search_public_marketplace_products(NULL)
                """
            )
            return {row["sku"] for row in rows}
    finally:
        await pool.close()


def test_public_marketplace_function_only_returns_opted_in_products(seeded_tenants):
    skus = asyncio.run(_public_marketplace_skus(_application_dsn()))
    assert seeded_tenants["sku_a"] in skus
    assert seeded_tenants["sku_b"] not in skus


async def _cross_tenant_product_category_rejected(
    dsn: str,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID,
) -> bool:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('app.tenant_id', $1, true)",
                    str(tenant_id),
                )
                try:
                    async with conn.transaction():
                        await conn.execute(
                            """
                            INSERT INTO tenant_data.products (
                                tenant_id, category_id, sku, name_en, name_bn, sell_price
                            ) VALUES ($1, $2, $3, 'Cross Tenant', 'অন্য টেন্যান্ট', 1)
                            """,
                            tenant_id,
                            category_id,
                            f"INT-CROSS-{uuid.uuid4().hex[:10]}",
                        )
                except asyncpg.ForeignKeyViolationError:
                    return True
                return False
    finally:
        await pool.close()


def test_product_cannot_reference_another_tenants_category(seeded_tenants):
    assert asyncio.run(
        _cross_tenant_product_category_rejected(
            _application_dsn(),
            seeded_tenants["tenant_a"],
            seeded_tenants["category_b"],
        )
    )
