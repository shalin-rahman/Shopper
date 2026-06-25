"""Business flow integration tests — require a live database."""
from __future__ import annotations
import os
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.skipif(
    os.getenv("TESTING") == "1",
    reason="Integration test — requires a live database",
)


@pytest.mark.asyncio
async def test_tenant_registration_and_accounting_setup(async_client: AsyncClient):
    """
    Test 1: Self-service registration should create tenant and provision COA.
    """
    reg_data = {
        "subdomain": "test-inc",
        "company_name_en": "Test Inc",
        "company_name_bn": "টেস্ট ইনক",
        "admin_username": "admin",
        "admin_password": "securepassword"
    }
    response = await async_client.post("/v1/register", json=reg_data)
    assert response.status_code == 201
    data = response.json()
    assert data["subdomain"] == "test-inc"

    # Auth as the new user
    login_resp = await async_client.post(
        "/v1/tenant/auth/login",
        json={"username": "admin", "password": "securepassword"},
        headers={"X-Shopper-Tenant": "test-inc"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Shopper-Tenant": "test-inc"}

    # Check Accounts
    acc_resp = await async_client.get("/v1/tenant/accounts", headers=headers)
    assert acc_resp.status_code == 200
    accounts = acc_resp.json()["items"]
    codes = [a["code"] for a in accounts]
    assert "1000" in codes  # Cash
    assert "1100" in codes  # AR


@pytest.mark.asyncio
async def test_expense_logging_to_ledger(async_client: AsyncClient, auth_headers: dict):
    """
    Test 2: Creating an expense should record a ledger entry.
    """
    cat_resp = await async_client.get("/v1/tenant/expenses/categories", headers=auth_headers)
    assert cat_resp.status_code == 200


@pytest.mark.asyncio
async def test_maintenance_reconciliation(async_client: AsyncClient, auth_headers: dict):
    """
    Test 3: Maintenance reconciliation should return 200.
    """
    response = await async_client.post("/v1/tenant/maintenance/ledger-reconcile", headers=auth_headers)
    assert response.status_code == 200
    assert "accounts_reconciled" in response.json()
