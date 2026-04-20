import pytest
from uuid import uuid4
from decimal import Decimal
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_pos_e2e_flow(client: AsyncClient, test_db):
    # 1. Setup Tenant and Staff (Assuming conftest handles base setup)
    subdomain = "test-pos-e2e"
    
    # 2. Add Product with Stock
    # First get staff token (mocked or via login)
    # For this test, we assume we have a valid staff context for 'demo' or similar
    # we'll use the 'demo' tenant which usually exists in test_db
    tenant = "demo"
    headers = {"Host": f"{tenant}.shopper.com"}
    
    # login as staff
    login_resp = await client.post(
        "/v1/tenant/auth/login",
        json={"username": "admin", "password": "password"},
        headers=headers
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    auth_headers = {**headers, "Authorization": f"Bearer {token}"}

    # Create Product
    product_data = {
        "sku": f"E2E-{uuid4().hex[:6]}",
        "name_en": "E2E Test Product",
        "name_bn": "ইটু্ই টেস্ট পণ্য",
        "buy_price": "100.00",
        "sell_price": "150.00",
        "vat_rate_pct": "15.0",
        "stock_quantity": 100
    }
    prod_resp = await client.post("/v1/tenant/products", json=product_data, headers=auth_headers)
    assert prod_resp.status_code == 201
    product_id = prod_resp.json()["id"]

    # 3. Simulate Mobile POS Offline Punch
    pos_payload = [{
        "id": str(uuid4()),
        "orderNumber": "POS-E2E-001",
        "total": 172.50, # 150 + 15% VAT
        "subtotal": 150.00,
        "taxAmount": 22.50,
        "customerName": "John Doe",
        "customerPhone": "01700000001",
        "items": [{
            "productId": product_id,
            "productName": "E2E Test Product",
            "quantity": 1,
            "unitPrice": 150.00,
            "vatRatePct": 15.0,
            "vatAmount": 22.50
        }],
        "createdAt": "2026-04-21T00:00:00Z"
    }]
    
    punch_resp = await client.post("/v1/tenant/pos/offline-punch", json=pos_payload, headers=auth_headers)
    assert punch_resp.status_code == 200
    assert len(punch_resp.json()["synced_local_ids"]) == 1

    # 4. Verify Stock Deduction
    get_prod = await client.get(f"/v1/tenant/products/{product_id}", headers=auth_headers)
    # Note: Backend should have deducted stock based on pos_router implementation
    # If the pos_router is just a stub, this will fail, reminding us to implement the logic.
    # We implemented the logic in previous turns.
    # Current stock should be 99
    assert get_prod.json()["stock_quantity"] == 99

    # 5. Verify Invoice Generation
    # The offline-punch should have created an invoice
    inv_resp = await client.get("/v1/tenant/invoices", headers=auth_headers)
    assert inv_resp.status_code == 200
    invoices = inv_resp.json()
    e2e_inv = next((i for i in invoices if i["invoice_no"] == "POS-E2E-001"), None)
    assert e2e_inv is not None
    assert Decimal(e2e_inv["total_amount"]) == Decimal("172.50")

    # 6. Verify Mushak 6.3 Receipt
    receipt_resp = await client.get(f"/v1/tenant/receipts/{e2e_inv['id']}", headers=auth_headers)
    assert receipt_resp.status_code == 200
    receipt_text = receipt_resp.text
    assert "Mushak 6.3" in receipt_text
    assert "E2E Test Prod" in receipt_text # backend truncates to 12 chars

    print("E2E POS Flow: SUCCESS")
