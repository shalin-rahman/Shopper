import os

import pytest
from starlette.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_products_no_db_returns_503(client: TestClient):
    r = client.get(
        "/v1/tenant/products",
        headers={"X-Shopper-Tenant": "demo"},
    )
    assert r.status_code == 503


def test_tenant_settings_no_db_returns_503(client: TestClient):
    r = client.get(
        "/v1/tenant/settings",
        headers={"X-Shopper-Tenant": "demo"},
    )
    assert r.status_code == 503


def test_storefront_products_requires_tenant(client: TestClient):
    r = client.get("/v1/storefront/products")
    assert r.status_code == 400


def test_storefront_products_no_db_returns_503(client: TestClient):
    r = client.get("/v1/storefront/products", headers={"X-Shopper-Tenant": "demo"})
    assert r.status_code == 503


def test_inventory_aging_no_db_returns_503(client: TestClient):
    r = client.get("/v1/tenant/reports/inventory-aging", headers={"X-Shopper-Tenant": "demo"})
    assert r.status_code == 503


def test_admin_disabled_without_configured_key(client: TestClient):
    os.environ.pop("SHOPPER_ADMIN_API_KEY", None)
    r = client.get("/v1/admin/tenants", headers={"X-Shopper-Admin-Key": "nope"})
    assert r.status_code == 503


def test_admin_unauthorized_when_key_set(client: TestClient):
    os.environ["SHOPPER_ADMIN_API_KEY"] = "secret"
    r = client.get("/v1/admin/tenants")
    assert r.status_code == 401


def test_ipn_requires_tenant_query(client: TestClient):
    r = client.post("/v1/tenant/payments/ipn/sslcommerz", json={})
    assert r.status_code == 422


def test_ipn_no_db_returns_503(client: TestClient):
    r = client.post("/v1/tenant/payments/ipn/sslcommerz?tenant=demo", json={})
    assert r.status_code == 503


def test_ipn_accepts_form_urlencoded_without_db(client: TestClient):
    """SSLCommerz posts application/x-www-form-urlencoded; ensure parser path is exercised."""
    r = client.post(
        "/v1/tenant/payments/ipn/sslcommerz?tenant=demo",
        data={
            "tran_id": "ORD-1",
            "val_id": "VAL-1",
            "amount": "100.00",
            "store_id": "",
            "status": "VALID",
        },
    )
    assert r.status_code == 503


def test_sslcommerz_ipn_rejects_wrong_store_when_configured():
    import asyncio

    from config import clear_settings_cache, get_settings
    import payments_router

    async def _run() -> None:
        gw = payments_router.SSLCommerzGateway(get_settings())
        assert not await gw.verify_ipn({"store_id": "other", "status": "VALID"})
        assert await gw.verify_ipn({"store_id": "my_store", "status": "VALID"})
        assert gw.ipn_payment_status({"status": "VALID"}) == "completed"
        assert gw.ipn_payment_status({"status": "FAILED"}) == "failed"

    os.environ["SSLCOMMERZ_STORE_ID"] = "my_store"
    clear_settings_cache()
    try:
        asyncio.run(_run())
    finally:
        os.environ.pop("SSLCOMMERZ_STORE_ID", None)
        clear_settings_cache()
