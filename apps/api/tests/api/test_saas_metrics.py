"""SaaS platform metrics and global endpoints — unit tests (no DB required)."""
import os
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_marketplace_global_search(async_client: AsyncClient):
    """Marketplace search should return a structured response even without DB."""
    res = await async_client.get("/v1/marketplace/search?q=test")
    # Endpoint is whitelisted in middleware; check it responds (may be 503 or 200)
    assert res.status_code in (200, 503)


@pytest.mark.asyncio
async def test_dunning_cron_action(async_client: AsyncClient):
    """Dunning cron endpoint should require admin key."""
    os.environ["SHOPPER_ADMIN_API_KEY"] = "super-secret"
    # Without admin key → 401
    res_fail = await async_client.post("/v1/admin/cron/dunning")
    assert res_fail.status_code == 401

    # With admin key → 200 or 503 (no db)
    headers = {"X-Shopper-Admin-Key": "super-secret"}
    res = await async_client.post("/v1/admin/cron/dunning", headers=headers)
    assert res.status_code in (200, 503)
    os.environ.pop("SHOPPER_ADMIN_API_KEY", None)


@pytest.mark.asyncio
async def test_product_barcode_label_endpoint(async_client: AsyncClient, staff_token_headers):
    """Barcode label endpoint should 503 gracefully for a non-existent product when DB is unavailable."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    res = await async_client.get(
        f"/v1/tenant/products/{fake_uuid}/label",
        headers=staff_token_headers,
    )
    # Without DB the route returns 503
    assert res.status_code == 503
