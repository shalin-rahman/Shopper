"""Product, invoice, return and refund flows through the API on the scratch database."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from core.config import clear_settings_cache
from routers.auth import pwd_context
from tests.integration.seed import drop_tenant, seed_demo

pytestmark = pytest.mark.skipif(
    not (
        os.getenv("INTEGRATION_TEST") == "1"
        and os.getenv("MIGRATE_DATABASE_URL")
        and os.getenv("DATABASE_URL")
    ),
    reason="Set INTEGRATION_TEST=1, MIGRATE_DATABASE_URL and DATABASE_URL to run the commerce flows",
)

MANAGER_PASSWORD = "password-manager"


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


@asynccontextmanager
async def _tenant_client():
    """Seed a tenant, start the app, and yield (client, admin headers, seeded, dsn)."""
    from main import app

    dsn = _migrate_dsn()
    seeded = await seed_demo(dsn)
    try:
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url=f"http://{seeded['subdomain']}.localhost",
            ) as client:
                auth = await _login(client, seeded["username"], seeded["password"])
                yield client, auth, seeded, dsn
    finally:
        await drop_tenant(dsn, seeded["tenant_id"])


async def _login(client: AsyncClient, username: str, password: str) -> dict:
    resp = await client.post("/v1/tenant/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_product(client: AsyncClient, auth: dict, stock: int) -> str:
    resp = await client.post(
        "/v1/tenant/products",
        json={
            "sku": f"CF-{uuid4().hex[:6]}",
            "name_en": "Flow Product",
            "name_bn": "পণ্য",
            "buy_price": "60.00",
            "sell_price": "100.00",
            "vat_rate_pct": "15.0",
            "stock_quantity": stock,
        },
        headers=auth,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_invoice(client: AsyncClient, auth: dict, product_id: str, qty: int) -> dict:
    resp = await client.post(
        "/v1/tenant/invoices",
        json={
            "invoice_no": f"INV-{uuid4().hex[:8]}",
            "lines": [
                {
                    "product_id": product_id,
                    "description": "Flow Product",
                    "qty": str(qty),
                    "unit_price": "100.00",
                    "vat_rate_pct": "15.0",
                }
            ],
        },
        headers=auth,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _stock(dsn: str, tenant_id: UUID, product_id: str) -> tuple[Decimal, Decimal]:
    """Return (products.stock_quantity, main-branch stock_levels.quantity)."""
    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            """
            SELECT p.stock_quantity, l.quantity
              FROM tenant_data.products p
              LEFT JOIN tenant_data.stock_levels l
                ON l.product_id = p.id
               AND l.branch_id = (SELECT id FROM tenant_data.branches WHERE tenant_id = $1 AND is_main)
             WHERE p.id = $2 AND p.tenant_id = $1
            """,
            tenant_id,
            UUID(product_id),
        )
    finally:
        await conn.close()
    return Decimal(str(row["stock_quantity"])), Decimal(str(row["quantity"] or 0))


async def _fetch(dsn: str, sql: str, *args) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(dsn)
    try:
        return await conn.fetch(sql, *args)
    finally:
        await conn.close()


async def test_product_create_records_opening_stock(live_settings):
    async with _tenant_client() as (client, auth, seeded, dsn):
        product_id = await _create_product(client, auth, 10)

        assert await _stock(dsn, seeded["tenant_id"], product_id) == (Decimal(10), Decimal(10))
        moves = await _fetch(
            dsn,
            "SELECT transaction_type, quantity, reason_code FROM tenant_data.stock_transactions "
            "WHERE tenant_id = $1 AND product_id = $2",
            seeded["tenant_id"],
            UUID(product_id),
        )
        assert len(moves) == 1
        assert moves[0]["transaction_type"] == "in"
        assert Decimal(str(moves[0]["quantity"])) == 10
        assert moves[0]["reason_code"] == "opening"


async def test_invoice_issue_then_cancel_moves_stock_and_vat(live_settings):
    async with _tenant_client() as (client, auth, seeded, dsn):
        product_id = await _create_product(client, auth, 10)
        invoice = await _create_invoice(client, auth, product_id, 3)
        assert invoice["status"] == "draft"

        issued = await client.post(f"/v1/tenant/invoices/{invoice['id']}/issue", headers=auth)
        assert issued.status_code == 200, issued.text
        assert issued.json()["status"] == "issued"
        assert await _stock(dsn, seeded["tenant_id"], product_id) == (Decimal(7), Decimal(7))

        vat_sql = (
            "SELECT qty, vat_amount FROM tenant_data.vat_sales_register_lines "
            "WHERE tenant_id = $1 AND mushak_form = '6.3' AND invoice_no = $2 ORDER BY created_at"
        )
        lines = await _fetch(dsn, vat_sql, seeded["tenant_id"], invoice["invoice_no"])
        assert len(lines) == 1
        assert Decimal(str(lines[0]["vat_amount"])) == Decimal("45")

        cancelled = await client.post(f"/v1/tenant/invoices/{invoice['id']}/cancel", headers=auth)
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
        assert await _stock(dsn, seeded["tenant_id"], product_id) == (Decimal(10), Decimal(10))

        lines = await _fetch(dsn, vat_sql, seeded["tenant_id"], invoice["invoice_no"])
        assert len(lines) == 2
        assert sum(Decimal(str(r["vat_amount"])) for r in lines) == 0
        assert sum(Decimal(str(r["qty"])) for r in lines) == 0


async def test_issue_above_stock_is_refused_and_changes_nothing(live_settings):
    async with _tenant_client() as (client, auth, seeded, dsn):
        product_id = await _create_product(client, auth, 2)
        invoice = await _create_invoice(client, auth, product_id, 5)

        resp = await client.post(f"/v1/tenant/invoices/{invoice['id']}/issue", headers=auth)
        assert resp.status_code == 409, resp.text

        assert await _stock(dsn, seeded["tenant_id"], product_id) == (Decimal(2), Decimal(2))
        got = await client.get(f"/v1/tenant/invoices/{invoice['id']}", headers=auth)
        assert got.json()["status"] == "draft"
        assert not await _fetch(
            dsn,
            "SELECT 1 FROM tenant_data.vat_sales_register_lines WHERE tenant_id = $1 AND invoice_no = $2",
            seeded["tenant_id"],
            invoice["invoice_no"],
        )
        outs = await _fetch(
            dsn,
            "SELECT 1 FROM tenant_data.stock_transactions WHERE tenant_id = $1 AND transaction_type = 'out'",
            seeded["tenant_id"],
        )
        assert not outs


async def test_partial_return_writes_credit_note_and_blocks_over_return(live_settings):
    async with _tenant_client() as (client, auth, seeded, dsn):
        product_id = await _create_product(client, auth, 10)
        invoice = await _create_invoice(client, auth, product_id, 4)
        issued = await client.post(f"/v1/tenant/invoices/{invoice['id']}/issue", headers=auth)
        assert issued.status_code == 200, issued.text

        ret = await client.post(
            "/v1/tenant/invoices/returns",
            json={"invoice_id": invoice["id"], "reason": "Damaged", "items": [{"product_id": product_id, "qty": "1"}]},
            headers=auth,
        )
        assert ret.status_code == 201, ret.text
        note = ret.json()
        assert Decimal(str(note["total_adjustment"])) > 0
        assert await _stock(dsn, seeded["tenant_id"], product_id) == (Decimal(7), Decimal(7))

        vat = await _fetch(
            dsn,
            "SELECT qty, vat_amount, total_amount FROM tenant_data.vat_sales_register_lines "
            "WHERE tenant_id = $1 AND mushak_form = '6.7' AND invoice_no = $2",
            seeded["tenant_id"],
            note["note_no"],
        )
        assert len(vat) == 1
        assert Decimal(str(vat[0]["vat_amount"])) == Decimal("-15")
        assert Decimal(str(vat[0]["total_amount"])) < 0

        over = await client.post(
            "/v1/tenant/invoices/returns",
            json={"invoice_id": invoice["id"], "reason": "Again", "items": [{"product_id": product_id, "qty": "4"}]},
            headers=auth,
        )
        assert 400 <= over.status_code < 500, over.text
        assert await _stock(dsn, seeded["tenant_id"], product_id) == (Decimal(7), Decimal(7))


async def test_refund_raises_invoice_balance_and_caps_at_payment(live_settings):
    async with _tenant_client() as (client, auth, seeded, dsn):
        product_id = await _create_product(client, auth, 10)
        invoice = await _create_invoice(client, auth, product_id, 1)
        issued = await client.post(f"/v1/tenant/invoices/{invoice['id']}/issue", headers=auth)
        assert issued.status_code == 200, issued.text

        conn = await asyncpg.connect(dsn)
        try:
            payment_id = await conn.fetchval(
                """
                INSERT INTO tenant_data.payments (tenant_id, gateway, amount, status, invoice_id, ipn_verified)
                VALUES ($1, 'bkash', 115, 'completed', $2, true) RETURNING id
                """,
                seeded["tenant_id"],
                UUID(invoice["id"]),
            )
            await conn.execute(
                """
                INSERT INTO tenant_data.staff (tenant_id, username, password_hash, full_name, role, branch_id)
                VALUES ($1, 'manager', $2, 'Flow Manager', 'manager', $3)
                """,
                seeded["tenant_id"],
                pwd_context.hash(MANAGER_PASSWORD),
                seeded["branch_id"],
            )
        finally:
            await conn.close()

        paid = (await client.get(f"/v1/tenant/invoices/{invoice['id']}", headers=auth)).json()
        assert Decimal(str(paid["balance_due"])) == 0
        assert paid["status"] == "paid"

        manager = await _login(client, "manager", MANAGER_PASSWORD)
        refund = await client.post(
            f"/v1/tenant/payments/{payment_id}/refunds",
            json={"amount": "40", "reference": "RF-1"},
            headers=manager,
        )
        assert refund.status_code == 201, refund.text

        after = (await client.get(f"/v1/tenant/invoices/{invoice['id']}", headers=auth)).json()
        assert Decimal(str(after["balance_due"])) == Decimal("40")
        assert after["status"] == "partially_paid"

        too_much = await client.post(
            f"/v1/tenant/payments/{payment_id}/refunds",
            json={"amount": "80", "reference": "RF-2"},
            headers=manager,
        )
        assert too_much.status_code == 409, too_much.text
        final = (await client.get(f"/v1/tenant/invoices/{invoice['id']}", headers=auth)).json()
        assert Decimal(str(final["balance_due"])) == Decimal("40")


async def test_stock_without_cost_layers_is_sold_at_backfilled_cost(live_settings):
    migration = (
        Path(__file__).resolve().parents[4] / "database" / "migrations" / "033_cost_layer_after_insert.sql"
    ).read_text(encoding="utf-8")
    async with _tenant_client() as (client, auth, seeded, dsn):
        conn = await asyncpg.connect(dsn)
        try:
            # Stock written straight to the tables, as old data was, so it has no cost layer.
            product_id = await conn.fetchval(
                """
                INSERT INTO tenant_data.products (tenant_id, sku, name_en, name_bn, buy_price, sell_price, stock_quantity)
                VALUES ($1, $2, 'Legacy', 'পুরনো', 60, 100, 5) RETURNING id
                """,
                seeded["tenant_id"],
                f"LEG-{uuid4().hex[:6]}",
            )
            await conn.execute(
                "INSERT INTO tenant_data.stock_levels (tenant_id, branch_id, product_id, quantity) VALUES ($1, $2, $3, 5)",
                seeded["tenant_id"],
                seeded["branch_id"],
                product_id,
            )
            await conn.execute(migration)
            layers = await conn.fetch(
                "SELECT transaction_id, quantity_remaining, unit_cost FROM tenant_data.cost_layers WHERE product_id = $1",
                product_id,
            )
            assert len(layers) == 1
            assert layers[0]["transaction_id"] is None
            assert Decimal(str(layers[0]["quantity_remaining"])) == 5
            assert Decimal(str(layers[0]["unit_cost"])) == 60

            # A second run adds nothing.
            await conn.execute(migration)
            assert await conn.fetchval(
                "SELECT count(*) FROM tenant_data.cost_layers WHERE product_id = $1", product_id
            ) == 1
        finally:
            await conn.close()

        invoice = await _create_invoice(client, auth, str(product_id), 2)
        issued = await client.post(f"/v1/tenant/invoices/{invoice['id']}/issue", headers=auth)
        assert issued.status_code == 200, issued.text
        out = await _fetch(
            dsn,
            "SELECT unit_cost FROM tenant_data.stock_transactions WHERE product_id = $1 AND transaction_type = 'out'",
            product_id,
        )
        assert len(out) == 1
        assert Decimal(str(out[0]["unit_cost"])) == 60
