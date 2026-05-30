"""Admin tenant data export — integration test (requires live database)."""
import os
import pytest
from uuid import uuid4

pytestmark = pytest.mark.skipif(
    os.getenv("TESTING") == "1",
    reason="Integration test — requires a live database",
)


@pytest.mark.asyncio
async def test_tenant_data_export(async_client, settings):
    """
    Verifies that a super admin can export all data for a tenant.
    """
    if not settings.shopper_admin_api_key:
        pytest.skip("SHOPPER_ADMIN_API_KEY not configured")

    admin_headers = {"X-Shopper-Admin-Key": settings.shopper_admin_api_key}

    # 1. List tenants to get an ID
    list_resp = await async_client.get("/v1/admin/tenants", headers=admin_headers)
    assert list_resp.status_code == 200
    tenants = list_resp.json()["items"]

    if not tenants:
        pytest.skip("No tenants available for export test")

    tenant_id = tenants[0]["id"]

    # 2. Export Data
    export_resp = await async_client.get(f"/v1/admin/tenants/{tenant_id}/export", headers=admin_headers)
    assert export_resp.status_code == 200
    data = export_resp.json()

    assert "tenant_meta" in data
    assert "data" in data
    assert "products" in data["data"]
    assert "invoices" in data["data"]
