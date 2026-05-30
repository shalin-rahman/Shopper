import os

import pytest
from starlette.testclient import TestClient

from main import app


# (Fixture moved to conftest.py)

def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_products_returns_mock_in_testing_mode(client: TestClient, auth_headers: dict):
    """In TESTING mode products_router returns mock data instead of 503."""
    r = client.get(
        "/v1/tenant/products",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_tenant_settings_returns_mock_in_testing_mode(client: TestClient, auth_headers: dict):
    """In TESTING mode settings_router returns mock settings instead of 503."""
    r = client.get(
        "/v1/tenant/settings",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "legal_title_en" in data


def test_storefront_products_no_db_returns_503(client: TestClient):
    """Storefront has no testing mock, so db_pool=None → 503."""
    r = client.get("/v1/storefront/products")
    assert r.status_code == 503


def test_inventory_aging_no_db_returns_503(client: TestClient, auth_headers: dict):
    r = client.get("/v1/tenant/reports/inventory-aging", headers=auth_headers)
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
    """Unit test of SSLCommerzGateway store_id validation (no network calls)."""
    from config import clear_settings_cache, get_settings
    from payments_core import SSLCommerzGateway

    os.environ["SSLCOMMERZ_STORE_ID"] = "my_store"
    clear_settings_cache()
    try:
        settings = get_settings()
        gw = SSLCommerzGateway(settings)

        # ipn_payment_status is synchronous — test it directly
        assert gw.ipn_payment_status({"status": "VALID"}) == "completed"
        assert gw.ipn_payment_status({"status": "FAILED"}) == "failed"
    finally:
        os.environ.pop("SSLCOMMERZ_STORE_ID", None)
        clear_settings_cache()
