"""Marketplace search, storefront catalog and tenant status checks on the scratch database."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from core.config import clear_settings_cache
from tests.integration.seed import drop_tenant, seed_demo

pytestmark = pytest.mark.skipif(
    not (
        os.getenv("INTEGRATION_TEST") == "1"
        and os.getenv("MIGRATE_DATABASE_URL")
        and os.getenv("DATABASE_URL")
    ),
    reason="Set INTEGRATION_TEST=1, MIGRATE_DATABASE_URL and DATABASE_URL to run the public and lifecycle tests",
)

# Not a dev host and not under the platform root, so the request carries no tenant.
NO_TENANT_BASE = "http://shopper.example"


def _migrate_dsn() -> str:
    from core.config import get_settings

    settings = get_settings()
    return settings.normalize_dsn(settings.migrate_database_url)


@pytest.fixture
def live_settings(monkeypatch):
    # conftest sets TESTING=1, which makes the app skip the database.
    monkeypatch.setenv("TESTING", "0")
    monkeypatch.setenv("ALLOW_TENANT_OVERRIDE", "true")
    clear_settings_cache()
    yield
    clear_settings_cache()


@asynccontextmanager
async def _two_shops():
    """Seed shops A and B, each with one opted-in and one opted-out product named with a shared word."""
    from main import app

    dsn = _migrate_dsn()
    word = f"mkt{uuid4().hex[:8]}"
    shops: list[dict] = []
    try:
        for _ in range(2):
            shops.append(await seed_demo(dsn))
        async with app.router.lifespan_context(app):
            for shop in shops:
                async with _client(app, shop["subdomain"]) as client:
                    auth = await _login(client, shop["username"], shop["password"])
                    shop["listed"] = await _create_product(client, auth, word, listed=True)
                    shop["hidden"] = await _create_product(client, auth, word, listed=False)
            yield app, shops, word, dsn
    finally:
        for shop in shops:
            await drop_tenant(dsn, shop["tenant_id"])


def _client(app, subdomain: str | None) -> AsyncClient:
    base = f"http://{subdomain}.localhost" if subdomain else NO_TENANT_BASE
    return AsyncClient(transport=ASGITransport(app=app), base_url=base)


async def _login(client: AsyncClient, username: str, password: str) -> dict:
    resp = await client.post("/v1/tenant/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_product(client: AsyncClient, auth: dict, word: str, *, listed: bool) -> str:
    resp = await client.post(
        "/v1/tenant/products",
        json={
            "sku": f"MK-{uuid4().hex[:6]}",
            "name_en": f"{word} {'listed' if listed else 'hidden'}",
            "name_bn": "পণ্য",
            "buy_price": "60.00",
            "sell_price": "100.00",
            "vat_rate_pct": "15.0",
            "stock_quantity": 5,
            "marketplace_enabled": listed,
        },
        headers=auth,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _set_status(dsn: str, tenant_id: UUID, status: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("UPDATE platform.tenants SET status = $1 WHERE id = $2", status, tenant_id)
    finally:
        await conn.close()


async def _search(app, word: str) -> dict:
    async with _client(app, None) as client:
        resp = await client.get("/v1/marketplace/search", params={"q": word})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_marketplace_search_returns_only_opted_in_products(live_settings):
    async with _two_shops() as (app, shops, word, _dsn):
        body = await _search(app, word)

    found = {p["id"]: p["tenant_subdomain"] for p in body["products"]}
    assert found == {shop["listed"]: shop["subdomain"] for shop in shops}
    assert body["total"] == 2
    assert body["tenant"] == "global-marketplace"


@pytest.mark.asyncio
async def test_storefront_lists_only_its_own_opted_in_products(live_settings):
    async with _two_shops() as (app, shops, word, _dsn):
        shop_a = shops[0]
        async with _client(app, shop_a["subdomain"]) as client:
            resp = await client.get("/v1/storefront/products", params={"q": word})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [p["id"] for p in body["products"]] == [shop_a["listed"]]
    assert body["total"] == 1
    assert body["tenant"] == shop_a["subdomain"]


@pytest.mark.asyncio
async def test_blocked_tenant_statuses_cannot_log_in_or_list(live_settings):
    async with _two_shops() as (app, shops, word, dsn):
        shop_a, shop_b = shops
        for status in ("suspended", "canceled", "pending", "deleted"):
            await _set_status(dsn, shop_a["tenant_id"], status)
            async with _client(app, shop_a["subdomain"]) as client:
                login = await client.post(
                    "/v1/tenant/auth/login",
                    json={"username": shop_a["username"], "password": shop_a["password"]},
                )
                catalog = await client.get("/v1/storefront/products")
            assert login.status_code == 404, (status, login.text)
            assert login.json()["detail"] == "Unknown or inactive tenant"
            assert catalog.status_code == 404, (status, catalog.text)

            body = await _search(app, word)
            assert [p["id"] for p in body["products"]] == [shop_b["listed"]], status


@pytest.mark.asyncio
async def test_trialing_and_past_due_tenants_can_log_in_and_list(live_settings):
    async with _two_shops() as (app, shops, word, dsn):
        shop_a = shops[0]
        for status in ("trialing", "past_due"):
            await _set_status(dsn, shop_a["tenant_id"], status)
            async with _client(app, shop_a["subdomain"]) as client:
                await _login(client, shop_a["username"], shop_a["password"])

            body = await _search(app, word)
            assert shop_a["listed"] in {p["id"] for p in body["products"]}, status
