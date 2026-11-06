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
        "stock_quantity": 50,
        "sell_price": 100,
        "vat_rate_pct": 5
    }, headers=auth_headers)

    # 2. Create the destination branch, then transfer from main
    b_resp = await async_client.post("/v1/tenant/branches", json={
        "name": "Branch B",
        "code": f"B{uuid4().hex[:6]}",
    }, headers=auth_headers)
    assert b_resp.status_code == 201
    to_branch_id = b_resp.json()["id"]

    transfer_payload = {
        "sku": "TX-001",
        "qty": 50,
        "to_branch_id": to_branch_id,
    }
    resp = await async_client.post("/v1/tenant/inventory/transfer", json=transfer_payload, headers=auth_headers)
    assert resp.status_code == 201
    tx_id = resp.json()["id"]

    # The product total is unchanged; the stock just sits at the other branch.
    p_after = await async_client.get(f"/v1/tenant/products/{p_resp.json()['id']}", headers=auth_headers)
    assert float(p_after.json()["stock_quantity"]) == 50

    # 3. Get Mushak 6.5 PDF
    pdf_resp = await async_client.get(f"/v1/tenant/inventory/transfer/{tx_id}/mushak-6-5", headers=auth_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
