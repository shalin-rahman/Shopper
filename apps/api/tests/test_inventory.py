"""Inventory transfer & Mushak 6.5 — integration test (requires live database)."""
import os
import pytest
from uuid import uuid4

pytestmark = pytest.mark.skipif(
    os.getenv("TESTING") == "1",
    reason="Integration test — requires a live database",
)


@pytest.mark.asyncio
async def test_stock_transfer_and_mushak_6_5(async_client, auth_headers):
    """
    Test recording a stock transfer and generating Mushak 6.5 PDF.
    """
    # 1. Create a product
    p_resp = await async_client.post("/v1/tenant/products", json={
        "sku": "TX-001",
        "name_en": "Transfer Item",
        "name_bn": "স্থানান্তর পণ্য",
        "unit": "pcs",
        "sell_price": 100,
        "vat_rate_pct": 5
    }, headers=auth_headers)

    # 2. Record Transfer
    transfer_payload = {
        "sku": "TX-001",
        "qty": 50,
        "to_location": "Branch B"
    }
    resp = await async_client.post("/v1/tenant/inventory/transfer", json=transfer_payload, headers=auth_headers)
    assert resp.status_code == 201
    tx_id = resp.json()["id"]

    # 3. Get Mushak 6.5 PDF
    pdf_resp = await async_client.get(f"/v1/tenant/inventory/transfer/{tx_id}/mushak-6-5", headers=auth_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
