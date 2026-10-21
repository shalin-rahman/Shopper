from types import SimpleNamespace
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from redis_client import build_ipn_idempotency_key, ipn_already_processed, ipn_record_processed
from routers.payments import _ipn_refs, _pool
from schemas.payment import PaymentGateway
from schemas.payment import PaymentCreate
from services.payment_gateway import BKashGateway, NagadGateway, SSLCommerzGateway
from services.payment_settlement import reserve_invoice_payment


def test_build_ipn_idempotency_key_is_stable_and_unique():
    key = build_ipn_idempotency_key("demo", "sslcommerz", "order-123", "txn-abc")
    assert key == "shopper:ipn:v1:demo:sslcommerz:txn-abc"

    fallback = build_ipn_idempotency_key("demo", "sslcommerz", "order-123", "")
    assert fallback == "shopper:ipn:v1:demo:sslcommerz:order-123"

    with pytest.raises(ValueError):
        build_ipn_idempotency_key("demo", "sslcommerz", "", "")


def test_pool_helper_uses_request_app_state_pool():
    fake_pool = object()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_pool=fake_pool)))

    assert _pool(request) is fake_pool


def test_ipn_refs_extract_gateway_order_and_transaction_identifiers():
    assert _ipn_refs(
        PaymentGateway.sslcommerz,
        {"tran_id": "invoice-1", "val_id": "validation-1"},
    ) == ("invoice-1", "validation-1")
    assert _ipn_refs(
        PaymentGateway.nagad,
        {"orderId": "invoice-2", "payment_ref_id": "payment-2"},
    ) == ("invoice-2", "payment-2")
    assert _ipn_refs(PaymentGateway.bkash, {}) == ("", "")


@pytest.mark.asyncio
async def test_ipn_dedupe_round_trip():
    class FakeRedis:
        def __init__(self):
            self.store = {}

        async def get(self, key):
            return self.store.get(key)

        async def set(self, key, value, ex=None):
            self.store[key] = value

    client = FakeRedis()
    key = build_ipn_idempotency_key("demo", "bkash", "order-77", "txn-77")

    assert await ipn_already_processed(client, key) is False
    await ipn_record_processed(client, key, 60)
    assert await ipn_already_processed(client, key) is True


def test_payment_create_requires_a_positive_bounded_amount():
    with pytest.raises(ValidationError):
        PaymentCreate(gateway="sslcommerz", amount="0")

    with pytest.raises(ValidationError):
        PaymentCreate(gateway="sslcommerz", amount="1.00001")


def test_sslcommerz_status_requires_a_verified_terminal_result():
    assert SSLCommerzGateway(None).ipn_payment_status({"status": "VALIDATED"}) == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("gateway", "details"),
    [
        (BKashGateway(None), {"bkash_app_key": "configured"}),
        (NagadGateway(None), {"nagad_merchant_id": "configured"}),
    ],
)
async def test_mfs_gateways_fail_closed_without_verification_contract(gateway, details):
    with pytest.raises(HTTPException) as exc:
        await gateway.verify_ipn({"status": "success", "amount": "10"}, None, SimpleNamespace(**details))
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_sslcommerz_verification_returns_provider_verified_payment(monkeypatch):
    provider_result = {
        "status": "VALID",
        "tran_id": "order-1",
        "val_id": "validation-1",
        "amount": "25.00",
        "currency": "BDT",
    }

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return provider_result

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, params):
            assert params["val_id"] == "validation-1"
            return _Response()

    monkeypatch.setattr("services.payment_gateway.httpx.AsyncClient", lambda **kwargs: _Client())
    tenant_settings = SimpleNamespace(
        sslcommerz_store_id="store-1",
        sslcommerz_store_password="secret",
    )

    result = await SSLCommerzGateway(None).verify_ipn(
        {
            "store_id": "store-1",
            "tran_id": "order-1",
            "val_id": "validation-1",
            "amount": "25.00",
            "currency": "BDT",
        },
        SimpleNamespace(),
        tenant_settings,
    )

    assert result == {
        "tran_id": "order-1",
        "val_id": "validation-1",
        "amount": Decimal("25.00"),
        "currency": "BDT",
        "status": "VALIDATED",
    }


@pytest.mark.asyncio
async def test_sslcommerz_rejects_callback_claim_mismatching_provider_verification(monkeypatch):
    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "VALID",
                "tran_id": "order-1",
                "val_id": "validation-1",
                "amount": "25.00",
                "currency": "BDT",
            }

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, params):
            return _Response()

    monkeypatch.setattr("services.payment_gateway.httpx.AsyncClient", lambda **kwargs: _Client())
    result = await SSLCommerzGateway(None).verify_ipn(
        {
            "store_id": "store-1",
            "tran_id": "order-other",
            "val_id": "validation-1",
            "amount": "25.00",
            "currency": "BDT",
        },
        SimpleNamespace(),
        SimpleNamespace(
            sslcommerz_store_id="store-1",
            sslcommerz_store_password="secret",
        ),
    )

    assert result is None


class _InvoicePaymentConnection:
    def __init__(self, total_amount, status="draft", reserved=0):
        self.invoice = {
            "id": "invoice-id",
            "total_amount": total_amount,
            "status": status,
        }
        self.reserved = reserved

    async def fetchrow(self, query, invoice_id):
        assert "FOR UPDATE" in query
        return self.invoice

    async def fetchval(self, query, invoice_id):
        assert "status IN ('pending', 'completed')" in query
        return self.reserved


@pytest.mark.asyncio
async def test_invoice_payment_reserves_pending_and_completed_amounts():
    connection = _InvoicePaymentConnection("100", reserved="60")

    await reserve_invoice_payment(
        connection,
        "invoice-id",
        Decimal("40"),
        "BDT",
    )

    with pytest.raises(HTTPException) as exc:
        await reserve_invoice_payment(
            connection,
            "invoice-id",
            Decimal("40.01"),
            "BDT",
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_invoice_payment_rejects_cancelled_invoices_and_non_bdt():
    with pytest.raises(HTTPException) as currency_error:
        await reserve_invoice_payment(
            _InvoicePaymentConnection("100"),
            "invoice-id",
            Decimal("10"),
            "USD",
        )
    assert currency_error.value.status_code == 400

    with pytest.raises(HTTPException) as status_error:
        await reserve_invoice_payment(
            _InvoicePaymentConnection("100", status="cancelled"),
            "invoice-id",
            Decimal("10"),
            "BDT",
        )
    assert status_error.value.status_code == 400
