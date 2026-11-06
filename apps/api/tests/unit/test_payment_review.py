"""Gateway payments that complete on a cancelled or already-paid invoice are kept for review."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

import routers.payments as payments
from schemas.payment import PaymentGateway, PaymentReviewResolve

TENANT = UUID("44444444-4444-4444-8444-444444444444")
PAYMENT = UUID("55555555-5555-4555-8555-555555555555")
INVOICE = UUID("66666666-6666-4666-8666-666666666666")
NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)
MIGRATION = (
    Path(__file__).resolve().parents[4] / "database" / "migrations" / "029_payment_review.sql"
).read_text(encoding="utf-8")


def test_029_adds_review_columns_and_can_rerun():
    for column in ("review_reason TEXT", "review_note TEXT",
                   "review_resolved_at TIMESTAMPTZ", "review_resolved_by TEXT"):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in MIGRATION
    # Added once behind a check, so a rerun does not take a table lock to rebuild it.
    assert "conname = 'payments_review_reason_check'" in MIGRATION
    assert "DROP CONSTRAINT" not in MIGRATION
    assert "CHECK (review_reason IN ('invoice_cancelled', 'overpayment'))" in MIGRATION
    assert "CREATE INDEX IF NOT EXISTS idx_payments_open_review" in MIGRATION
    assert MIGRATION.strip().startswith("--") and "BEGIN;" in MIGRATION and "COMMIT;" in MIGRATION


class IpnConn:
    def __init__(self):
        self.executed = []

    async def fetchrow(self, sql, *args):
        return {
            "id": PAYMENT, "amount": Decimal("100"), "currency": "BDT", "status": "pending",
            "gateway_transaction_id": None, "order_id": "order-1", "invoice_id": INVOICE,
        }

    async def execute(self, sql, *args):
        self.executed.append((" ".join(sql.split()), args))


def _patch_ipn(monkeypatch, conn, problem):
    class Gateway:
        async def verify_ipn(self, data, settings, tenant_settings):
            return {"tran_id": "order-1", "val_id": "val-1", "amount": "100", "currency": "BDT"}

        def ipn_payment_status(self, data):
            return "completed"

    async def payload(request):
        return {}

    async def resolve(pool, sub):
        return {"id": TENANT, "dedicated_database_name": None}

    async def tenant_settings(request, tenant_id):
        return None

    async def late(conn, invoice_id, amount):
        return problem

    @asynccontextmanager
    async def transaction(request, tenant_id, db_name):
        yield conn

    monkeypatch.setattr(payments, "_ipn_payload_dict", payload)
    monkeypatch.setattr(payments, "_pool", lambda request: object())
    monkeypatch.setattr(payments, "resolve_tenant_id", resolve)
    monkeypatch.setattr(payments, "get_tenant_settings", tenant_settings)
    monkeypatch.setattr(payments, "get_gateway", lambda gateway, settings: Gateway())
    monkeypatch.setattr(payments, "late_settlement_problem", late)
    monkeypatch.setattr(payments, "tenant_transaction", transaction)


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", [None, "invoice_cancelled"])
async def test_ipn_stores_the_review_reason_on_the_payment(monkeypatch, problem):
    conn = IpnConn()
    _patch_ipn(monkeypatch, conn, problem)

    result = await payments.handle_ipn(object(), PaymentGateway.sslcommerz, SimpleNamespace(), tenant="demo")

    (sql, args), = conn.executed
    assert "review_reason = $4" in sql
    assert args[3] == problem
    assert result.get("needs_review") == problem


def _review_row(**overrides):
    row = {
        "id": PAYMENT, "gateway": "sslcommerz", "amount": Decimal("100"), "currency": "BDT",
        "status": "completed", "invoice_id": INVOICE, "review_reason": "overpayment",
        "review_note": None, "review_resolved_at": None, "review_resolved_by": None,
        "created_at": NOW, "updated_at": NOW,
    }
    row.update(overrides)
    return row


class ReviewConn:
    def __init__(self, row):
        self.row = row
        self.sql = []

    async def fetch(self, sql, *args):
        self.sql.append(" ".join(sql.split()))
        return [self.row] if self.row else []

    async def fetchrow(self, sql, *args):
        self.sql.append(" ".join(sql.split()))
        self.args = args
        return self.row


class Ctx:
    tenant_id = TENANT

    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def transaction(self):
        yield self.conn


@pytest.mark.asyncio
async def test_review_list_shows_only_open_items():
    conn = ReviewConn(_review_row())

    out = await payments.list_payment_reviews(Ctx(conn), {})

    assert [p.review_reason for p in out] == ["overpayment"]
    assert "review_reason IS NOT NULL AND review_resolved_at IS NULL" in conn.sql[0]


@pytest.mark.asyncio
async def test_resolve_review_records_note_and_user():
    conn = ReviewConn(_review_row(review_note="Refunded at gateway", review_resolved_at=NOW,
                                  review_resolved_by="user-1"))

    out = await payments.resolve_payment_review(
        Ctx(conn), PAYMENT, PaymentReviewResolve(note="Refunded at gateway"), {"uid": "user-1"},
    )

    assert out.review_resolved_by == "user-1"
    assert conn.args == (PAYMENT, "Refunded at gateway", "user-1")
    assert "review_resolved_at IS NULL" in conn.sql[0]


@pytest.mark.asyncio
async def test_resolve_review_404_when_nothing_open():
    with pytest.raises(HTTPException) as exc:
        await payments.resolve_payment_review(
            Ctx(ReviewConn(None)), PAYMENT, PaymentReviewResolve(note="x"), {"uid": "user-1"},
        )
    assert exc.value.status_code == 404


def test_resolve_review_needs_a_note():
    with pytest.raises(ValueError):
        PaymentReviewResolve(note="")
