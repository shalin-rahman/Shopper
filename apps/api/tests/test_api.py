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


def test_admin_disabled_without_configured_key(client: TestClient):
    os.environ.pop("SHOPPER_ADMIN_API_KEY", None)
    r = client.get("/v1/admin/tenants", headers={"X-Shopper-Admin-Key": "nope"})
    assert r.status_code == 503


def test_admin_unauthorized_when_key_set(client: TestClient):
    os.environ["SHOPPER_ADMIN_API_KEY"] = "secret"
    r = client.get("/v1/admin/tenants")
    assert r.status_code == 401
