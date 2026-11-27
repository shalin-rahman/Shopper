"""POS flow end to end through the API on the scratch database, with a seeded tenant."""

from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from core.config import clear_settings_cache
from tests.integration.seed import drop_tenant, seed_demo

pytestmark = pytest.mark.skipif(
    not (
        os.getenv("INTEGRATION_TEST") == "1"
        and os.getenv("MIGRATE_DATABASE_URL")
        and os.getenv("DATABASE_URL")
    ),
    reason="Set INTEGRATION_TEST=1, MIGRATE_DATABASE_URL and DATABASE_URL to run the POS flow",
)


def _migrate_dsn() -> str:
    from core.config import get_settings

    settings = get_settings()
    return settings.normalize_dsn(settings.migrate_database_url)


@pytest.fixture
def live_settings(monkeypatch):
    # conftest sets TESTING=1, which makes the app skip the database.
    monkeypatch.setenv("TESTING", "0")
    monkeypatch.setenv("ALLOW_TENANT_OVERRIDE", "true")
    clear_settings_cache()
    yield
    clear_settings_cache()


async def test_pos_e2e_flow(live_settings):
    from main import app

    dsn = _migrate_dsn()
    seeded = await seed_demo(dsn)
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url=f"http://{seeded['subdomain']}.localhost"
            ) as client:
                login = await client.post(
                    "/v1/tenant/auth/login",
                    json={"username": seeded["username"], "password": seeded["password"]},
                )
                assert login.status_code == 200, login.text
                auth = {"Authorization": f"Bearer {login.json()['access_token']}"}

                product = await client.post(
                    "/v1/tenant/products",
                    json={
                        "sku": f"E2E-{uuid4().hex[:6]}",
                        "name_en": "E2E Test Product",
                        "name_bn": "ই২ই পণ্য",
                        "buy_price": "100.00",
                        "sell_price": "150.00",
                        "vat_rate_pct": "15.0",
                        "stock_quantity": 100,
                    },
                    headers=auth,
                )
                assert product.status_code == 201, product.text
                product_id = product.json()["id"]

                punch = await client.post(
                    "/v1/tenant/pos/offline-punch",
                    json=[
                        {
                            "id": str(uuid4()),
                            "orderNumber": "POS-E2E-001",
                            "total": 172.50,
                            "subtotal": 150.00,
                            "taxAmount": 22.50,
                            "customerName": "John Doe",
                            "customerPhone": "01700000001",
                            "items": [
                                {
                                    "productId": product_id,
                                    "productName": "E2E Test Product",
                                    "quantity": 1,
                                    "unitPrice": 150.00,
                                    "vatRatePct": 15.0,
                                    "vatAmount": 22.50,
                                }
                            ],
                            "createdAt": "2026-04-21T00:00:00Z",
                        }
                    ],
                    headers=auth,
                )
                assert punch.status_code == 200, punch.text
                assert len(punch.json()["synced_local_ids"]) == 1

                got = await client.get(f"/v1/tenant/products/{product_id}", headers=auth)
                assert got.status_code == 200, got.text
                assert Decimal(str(got.json()["stock_quantity"])) == 99

                invoices = await client.get("/v1/tenant/invoices", headers=auth)
                assert invoices.status_code == 200, invoices.text
                body = invoices.json()
                rows = body["items"] if isinstance(body, dict) else body
                invoice = next((i for i in rows if i["invoice_no"] == "POS-E2E-001"), None)
                assert invoice is not None, rows
                assert Decimal(str(invoice["total_amount"])) == Decimal("172.50")

                receipt = await client.get(f"/v1/tenant/receipts/{invoice['id']}", headers=auth)
                assert receipt.status_code == 200, receipt.text
    finally:
        await drop_tenant(dsn, seeded["tenant_id"])
