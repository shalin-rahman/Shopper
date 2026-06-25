"""Full ERP production cycle — integration test (requires live database)."""
from __future__ import annotations
import os
import pytest
from httpx import AsyncClient
from uuid import uuid4

pytestmark = pytest.mark.skipif(
    os.getenv("TESTING") == "1",
    reason="Integration test — requires a live database (run with TESTING unset)",
)


@pytest.mark.asyncio
async def test_erp_full_production_cycle(async_client: AsyncClient):
    """
    Comprehensive test of the full ERP business cycle.
    """
    # 1. Register a new tenant
    tenant_sub = f"erp-test-{uuid4().hex[:6]}"
    reg_data = {
        "subdomain": tenant_sub,
        "company_name_en": "ERP Hardened Inc",
        "company_name_bn": "ইআরপি হার্ডেন্ড ইনক",
        "admin_username": "erp_admin",
        "admin_password": "ProductionPassword123!"
    }
    reg_resp = await async_client.post("/v1/register", json=reg_data)
    assert reg_resp.status_code == 201

    # Authenticate
    login_resp = await async_client.post(
        "/v1/tenant/auth/login",
        json={"username": "erp_admin", "password": "ProductionPassword123!"},
        headers={"X-Shopper-Tenant": tenant_sub}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Shopper-Tenant": tenant_sub}

    # 2. Verify Chart of Accounts (Provisioned)
    acc_resp = await async_client.get("/v1/tenant/accounts", headers=headers)
    accounts = acc_resp.json()["items"]
    account_codes = {a["code"]: a for a in accounts}
    assert "1000" in account_codes  # Cash
    assert "5000" in account_codes  # COGS

    # 3. Add a Supplier (Procurement)
    sup_data = {
        "code": "SUP-001",
        "name_en": "Global Logistics",
        "phone": "01700112233"
    }
    sup_resp = await async_client.post("/v1/tenant/suppliers", json=sup_data, headers=headers)
    assert sup_resp.status_code == 201

    # 4. Record an Expense (Accounting)
    cat_resp = await async_client.get("/v1/tenant/expenses/categories", headers=headers)
    categories = cat_resp.json()["items"]
    if categories:
        cat_id = categories[0]["id"]
        exp_data = {
            "category_id": cat_id,
            "amount": 1500.50,
            "description": "Office Stationery"
        }
        exp_resp = await async_client.post("/v1/tenant/expenses", json=exp_data, headers=headers)
        assert exp_resp.status_code == 201

    # 5. Customer & Collection Tracking
    cust_data = {
        "code": "CUST-99",
        "name_en": "Premium Client",
        "phone": "01800112233"
    }
    cust_resp = await async_client.post("/v1/tenant/customers", json=cust_data, headers=headers)
    cust_id = cust_resp.json()["id"]

    coll_data = {
        "customer_id": cust_id,
        "amount": 5000,
        "payment_method": "bkash",
        "reference_no": "TRX-BKASH-778"
    }
    coll_resp = await async_client.post("/v1/tenant/customers/collections", json=coll_data, headers=headers)
    assert coll_resp.status_code == 201

    # 6. Verify Collection List
    history_resp = await async_client.get(f"/v1/tenant/customers/collections?customer_id={cust_id}", headers=headers)
    assert len(history_resp.json()) >= 1
    assert history_resp.json()[0]["payment_method"] == "bkash"

    # 7. Mushak 6.1 (Purchase Register) Validation
    mushak_6_1_resp = await async_client.get(
        "/v1/tenant/reports/mushak-6-1?start_date=2024-01-01&end_date=2030-01-01",
        headers=headers
    )
    assert mushak_6_1_resp.status_code == 200

    # 8. Purchase Returns (Debit Note - Mushak 6.8)
    fake_po = str(uuid4())
    ret_data = {
        "po_id": fake_po,
        "reason": "Damaged goods",
        "items": []
    }
    ret_resp = await async_client.post("/v1/tenant/suppliers/returns", json=ret_data, headers=headers)
    assert ret_resp.status_code == 404  # Purchase Order not found handled gracefully

    print("\n✅ ERP Hardening Test Cycle Passed.")
