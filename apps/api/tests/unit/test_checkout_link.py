from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from core.config import Settings
from routers.invoices import create_checkout_link
from routers.storefront import storefront_initiate_payment, storefront_invoice_details
from services.checkout_link import CHECKOUT_LINK_TTL, sign_checkout, verify_checkout

SECRET = "x" * 40
TENANT = UUID("44444444-4444-4444-8444-444444444444")
OTHER_TENANT = UUID("55555555-5555-4555-8555-555555555555")
INVOICE = UUID("66666666-6666-4666-8666-666666666666")
NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
FUTURE = int(NOW.timestamp()) + 3600


def test_valid_token_verifies():
    token = sign_checkout(TENANT, INVOICE, FUTURE, SECRET)
    assert verify_checkout(TENANT, INVOICE, token, FUTURE, SECRET, now=NOW)


@pytest.mark.parametrize(
    "tenant, invoice, expires, secret",
    [
        (OTHER_TENANT, INVOICE, FUTURE, SECRET),
        (TENANT, UUID("77777777-7777-4777-8777-777777777777"), FUTURE, SECRET),
        (TENANT, INVOICE, FUTURE + 1, SECRET),
        (TENANT, INVOICE, FUTURE, "y" * 40),
    ],
)
def test_token_bound_to_tenant_invoice_expiry_and_secret(tenant, invoice, expires, secret):
    token = sign_checkout(TENANT, INVOICE, FUTURE, SECRET)
    assert not verify_checkout(tenant, invoice, token, expires, secret, now=NOW)


def test_expired_token_rejected():
    past = int(NOW.timestamp()) - 1
    token = sign_checkout(TENANT, INVOICE, past, SECRET)
    assert not verify_checkout(TENANT, INVOICE, token, past, SECRET, now=NOW)


def test_garbage_token_rejected():
    assert not verify_checkout(TENANT, INVOICE, "", FUTURE, SECRET, now=NOW)
    assert not verify_checkout(TENANT, INVOICE, "not-hex", FUTURE, SECRET, now=NOW)


class InvoiceConn:
    def __init__(self, exists=True, status="issued"):
        self.exists = exists
        self.status = status
        self.queried = False

    async def fetchrow(self, sql, *args):
        self.queried = True
        return {"id": INVOICE, "status": self.status} if self.exists else None

    async def fetch(self, sql, *args):
        return []


class FakeCtx:
    subdomain = "acme"
    tenant_id = TENANT

    def __init__(self, conn):
        self.conn = conn
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    @asynccontextmanager
    async def transaction(self):
        yield self.conn


def _settings():
    return Settings(_env_file=None, jwt_secret_key=SECRET)


async def test_checkout_view_rejects_bad_token_before_any_query():
    conn = InvoiceConn()
    with pytest.raises(HTTPException) as exc:
        await storefront_invoice_details(FakeCtx(conn), INVOICE, _settings(), t="bad", e=FUTURE)
    assert exc.value.status_code == 403
    assert not conn.queried


async def test_checkout_pay_rejects_bad_token():
    with pytest.raises(HTTPException) as exc:
        await storefront_initiate_payment(FakeCtx(InvoiceConn()), INVOICE, None, _settings(), t="bad", e=FUTURE)
    assert exc.value.status_code == 403


async def test_staff_link_contains_valid_token():
    link = await create_checkout_link(FakeCtx(InvoiceConn()), INVOICE, _settings(), {"role": "cashier"})
    assert link.invoice_id == INVOICE
    assert link.path == f"/checkout/{INVOICE}?t={link.token}&e={link.expires}"
    now = datetime.now(timezone.utc)
    assert link.expires <= int((now + CHECKOUT_LINK_TTL).timestamp()) + 1
    assert verify_checkout(TENANT, INVOICE, link.token, link.expires, SECRET, now=now)


async def test_staff_link_unknown_invoice_is_404():
    with pytest.raises(HTTPException) as exc:
        await create_checkout_link(FakeCtx(InvoiceConn(exists=False)), INVOICE, _settings(), {"role": "cashier"})
    assert exc.value.status_code == 404


@pytest.mark.parametrize("status", ["draft", "cancelled"])
async def test_staff_link_refuses_unpayable_invoice(status):
    with pytest.raises(HTTPException) as exc:
        await create_checkout_link(FakeCtx(InvoiceConn(status=status)), INVOICE, _settings(), {"role": "cashier"})
    assert exc.value.status_code == 409


@pytest.mark.parametrize("status", ["draft", "cancelled"])
async def test_invoice_qr_refuses_unpayable_invoice(status):
    import routers.invoices as invoices

    with pytest.raises(HTTPException) as exc:
        await invoices.get_invoice_qr(FakeCtx(InvoiceConn(status=status)), INVOICE, _settings(), {"role": "cashier"})
    assert exc.value.status_code == 409


async def test_invoice_qr_carries_signed_link_not_gateway_keys(monkeypatch):
    import routers.invoices as invoices

    captured = []

    class FakeQR:
        def __init__(self, **kwargs):
            pass

        def add_data(self, data):
            captured.append(data)

        def make(self, fit):
            pass

        def make_image(self, **kwargs):
            return SimpleNamespace(save=lambda buf, format: buf.write(b"png"))

    monkeypatch.setattr(invoices.qrcode, "QRCode", FakeQR)
    settings = Settings(_env_file=None, jwt_secret_key=SECRET, storefront_public_base_url="https://shop.example/")
    await invoices.get_invoice_qr(FakeCtx(InvoiceConn()), INVOICE, settings, {"role": "cashier"})

    url = captured[0]
    assert url.startswith(f"https://acme.shop.example/checkout/{INVOICE}?t=")
    assert "bkash" not in url and "nagad" not in url
    token = url.split("t=")[1].split("&")[0]
    expires = int(url.split("e=")[1])
    assert verify_checkout(TENANT, INVOICE, token, expires, SECRET)


async def test_invoice_qr_link_lasts_the_printed_days(monkeypatch):
    import routers.invoices as invoices

    captured = []

    class FakeQR:
        def __init__(self, **kwargs):
            pass

        def add_data(self, data):
            captured.append(data)

        def make(self, fit):
            pass

        def make_image(self, **kwargs):
            return SimpleNamespace(save=lambda buf, format: buf.write(b"png"))

    monkeypatch.setattr(invoices.qrcode, "QRCode", FakeQR)
    settings = Settings(_env_file=None, jwt_secret_key=SECRET, printed_checkout_link_days=90)
    before = datetime.now(timezone.utc)
    await invoices.get_invoice_qr(FakeCtx(InvoiceConn()), INVOICE, settings, {"role": "cashier"})

    expires = int(captured[0].split("e=")[1])
    assert int((before + timedelta(days=90)).timestamp()) <= expires <= int((before + timedelta(days=90)).timestamp()) + 2


@pytest.mark.parametrize("days", [0, 366])
def test_printed_link_days_must_be_1_to_365(days):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret_key=SECRET, printed_checkout_link_days=days)


def test_printed_link_days_defaults_to_30():
    assert Settings(_env_file=None, jwt_secret_key=SECRET).printed_checkout_link_days == 30
