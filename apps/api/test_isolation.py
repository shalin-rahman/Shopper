import pytest
import httpx
from uuid import UUID

API_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_tenant_isolation_leak():
    """
    Scenario: Tenant A should not see Tenant B's data.
    """
    async with httpx.AsyncClient(base_url=API_URL) as client:
        # Mocking auth for testing if needed
        headers_a = {"X-Shopper-Tenant": "tenant-a"}
        headers_b = {"X-Shopper-Tenant": "tenant-b"}
        
        # 1. Create product as Tenant A
        resp_create = await client.post(
            "/v1/tenant/products",
            json={
                "sku": "A-PROD-001",
                "name_en": "Tenant A Product",
                "unit": "pcs",
                "sell_price": 100
            },
            headers=headers_a
        )
        # Note: In real test, this needs a valid JWT if RBAC is enabled
        
        # 2. Try to fetch products as Tenant B
        resp_list = await client.get("/v1/tenant/products", headers=headers_b)
        
        if resp_list.status_code == 200:
            products = resp_list.json()
            for p in products:
                assert p["sku"] != "A-PROD-001", "Tenant B leaked Tenant A's data!"

@pytest.mark.asyncio
async def test_fail_closed_unknown_tenant():
    async with httpx.AsyncClient(base_url=API_URL) as client:
        resp = await client.get("/v1/tenant/products", headers={"X-Shopper-Tenant": "non-existent-tenant"})
        assert resp.status_code == 403, "Unknown tenant should return 403"
