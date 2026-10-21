import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_tenant_routes_require_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/tenant/products",
            json={
                "sku": "A-PROD-001",
                "name_en": "Tenant A Product",
                "unit": "pcs",
                "sell_price": 100
            },
            headers={"X-Shopper-Tenant": "tenant-a"},
        )

        assert response.status_code == 401

@pytest.mark.asyncio
async def test_unauthenticated_unknown_tenant_request_fails_closed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/tenant/products", headers={"X-Shopper-Tenant": "non-existent-tenant"})
        assert resp.status_code == 401, "Unauthenticated tenant requests must be rejected"
