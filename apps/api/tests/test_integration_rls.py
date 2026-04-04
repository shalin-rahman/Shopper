"""
Run against a real Postgres with schema loaded and tenant fixtures created via a migrate-capable role:
  set INTEGRATION_TEST=1 SHOPPER_MIGRATE_DATABASE_URL=postgresql+asyncpg://shopper_migrate:...@host:5432/shopper
  pytest apps/api/tests/test_integration_rls.py -q
"""

from __future__ import annotations

import asyncio
import os
import uuid
from importlib import reload

import asyncpg
import pytest

from config import clear_settings_cache, get_settings

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


async def _seed_tenant_data(dsn: str) -> tuple[str, str, uuid.UUID, uuid.UUID, str, str]:
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
            sku_a = f"INT-A-{uuid.uuid4().hex[:10]}"
            sku_b = f"INT-B-{uuid.uuid4().hex[:10]}"
            product_a = await conn.fetchval(
                """
                INSERT INTO tenant_data.products (
                    tenant_id, sku, name_en, name_bn, sell_price, vat_rate_pct, is_active
                ) VALUES ($1, $2, $3, $4, 100.00, 15, true)
                ON CONFLICT (tenant_id, sku) DO UPDATE SET name_en = EXCLUDED.name_en
                RETURNING id
                """,
                tenant_a,
                sku_a,
                "Product A",
                "পণ্য এ",
            )
            product_b = await conn.fetchval(
                """
                INSERT INTO tenant_data.products (
                    tenant_id, sku, name_en, name_bn, sell_price, vat_rate_pct, is_active
                ) VALUES ($1, $2, $3, $4, 120.00, 15, true)
                ON CONFLICT (tenant_id, sku) DO UPDATE SET name_en = EXCLUDED.name_en
                RETURNING id
                """,
                tenant_b,
                sku_b,
                "Product B",
                "পণ্য বি",
            )
    await pool.close()
    return sub_a, sub_b, tenant_a, tenant_b, sku_a, sku_b


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
    sub_a, sub_b, tenant_a, tenant_b, sku_a, sku_b = asyncio.run(_seed_tenant_data(dsn))
    yield {
        "sub_a": sub_a,
        "sub_b": sub_b,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "sku_a": sku_a,
        "sku_b": sku_b,
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


def test_tenant_a_cannot_see_tenant_b_products(client, seeded_tenants):
    r = client.get(
        "/v1/tenant/products",
        headers={"X-Shopper-Tenant": seeded_tenants["sub_a"]},
    )
    assert r.status_code == 200, r.text
    skus = {item["sku"] for item in r.json()}
    assert seeded_tenants["sku_a"] in skus
    assert seeded_tenants["sku_b"] not in skus

    r = client.get(
        "/v1/tenant/products",
        headers={"X-Shopper-Tenant": seeded_tenants["sub_b"]},
    )
    assert r.status_code == 200, r.text
    skus = {item["sku"] for item in r.json()}
    assert seeded_tenants["sku_b"] in skus
    assert seeded_tenants["sku_a"] not in skus


def test_tenant_product_fetch_isolation(client, seeded_tenants):
    r = client.get(
        f"/v1/tenant/products/{seeded_tenants['tenant_a']}",
        headers={"X-Shopper-Tenant": seeded_tenants["sub_b"]},
    )
    assert r.status_code == 404
