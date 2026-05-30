"""High-value invoice compliance — integration test (requires live database)."""
import os
import pytest
from decimal import Decimal
from uuid import uuid4

pytestmark = pytest.mark.skipif(
    os.getenv("TESTING") == "1",
    reason="Integration test — requires a live database",
)


@pytest.mark.asyncio
async def test_high_value_invoice_enforcement(async_client, auth_headers):
    """
    Verifies that invoices >= 200k require a customer with BIN/TIN/NID.
    """
    # 1. Create a high-value invoice without customer (should fail)
    high_val_payload = {
        "invoice_no": "HV-001",
        "lines": [{
            "description": "Premium Asset",
            "qty": 2,
            "unit_price": 150000,  # Total 300,000
            "vat_rate_pct": 15
        }]
    }

    resp = await async_client.post("/v1/tenant/invoices", json=high_val_payload, headers=auth_headers)
    assert resp.status_code == 400
    assert "Customer ID is required" in resp.json()["detail"]

    # 2. Create customer without BIN/TIN/NID
    cust_resp = await async_client.post("/v1/tenant/customers", json={
        "code": "CUST-LOW-INFO",
        "name_en": "Anonymous",
        "name_bn": "অজ্ঞাত",
    }, headers=auth_headers)
    cust_id = cust_resp.json()["id"]

    # 3. Try high-value invoice with this low-info customer (should fail)
    high_val_payload["customer_id"] = cust_id
    resp = await async_client.post("/v1/tenant/invoices", json=high_val_payload, headers=auth_headers)
    assert resp.status_code == 400
    assert "must have a valid TIN, NID, or BIN" in resp.json()["detail"]
