"""Refunds on a completed payment are recorded and can never add up to more than the payment."""

from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from routers.payments import create_payment_refund, list_payment_refunds
from schemas import PaymentRefundCreate

TENANT = UUID(int=9)
PAY = UUID(int=1)
INV = UUID(int=2)
CN = UUID(int=3)
MANAGER = {"uid": str(UUID(int=50)), "role": "manager", "tid": "t"}


def _flat(sql):
    return " ".join(sql.split())


class Conn:
    def __init__(self, payment=None, refunded="0", credit_note_found=True):
        self.payment = payment
        self.refunded = Decimal(refunded)
        self.credit_note_found = credit_note_found
        self.sql = []
        self.inserted = None

    async def fetchrow(self, sql, *args):
        self.sql.append(_flat(sql))
        if "FROM tenant_data.payments" in sql:
            return self.payment
        if "INSERT INTO tenant_data.payment_refunds" in sql:
            self.inserted = args
            return {"id": UUID(int=77), "payment_id": args[1], "amount": args[3]}
        raise AssertionError(sql)

    async def fetchval(self, sql, *args):
        self.sql.append(_flat(sql))
        if "FROM tenant_data.payments" in sql:
            return 1 if self.payment else None
        if "FROM tenant_data.credit_notes" in sql:
            assert args == (CN, INV)
            return 1 if self.credit_note_found else None
        assert "FROM tenant_data.payment_refunds" in sql and args == (PAY,)
        return self.refunded

    async def fetch(self, sql, *args):
        self.sql.append(_flat(sql))
        return [{"id": UUID(int=77), "amount": Decimal("5")}]


class Tx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class Ctx:
    tenant_id = TENANT

    def __init__(self, conn):
        self.conn = conn

    def transaction(self):
        return Tx(self.conn)


def _payment(status="completed", amount="100"):
    return {"id": PAY, "invoice_id": INV, "amount": Decimal(amount), "status": status}


def _body(amount="40"):
    return PaymentRefundCreate(amount=Decimal(amount), reference="BK-R1")


@pytest.mark.asyncio
async def test_refund_is_recorded_against_the_locked_payment():
    conn = Conn(_payment(), refunded="60")

    out = await create_payment_refund(Ctx(conn), PAY, _body("40"), MANAGER)

    assert out["id"] == UUID(int=77)
    assert "FOR UPDATE" in conn.sql[0]
    tenant_id, payment_id, invoice_id, amount, reference, note, credit_note_id, created_by = conn.inserted
    assert (tenant_id, payment_id, invoice_id, amount) == (TENANT, PAY, INV, Decimal("40"))
    assert reference == "BK-R1" and note is None and credit_note_id is None
    assert created_by == UUID(int=50)


@pytest.mark.asyncio
async def test_missing_payment_is_404():
    with pytest.raises(HTTPException) as exc:
        await create_payment_refund(Ctx(Conn(None)), PAY, _body(), MANAGER)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "failed", "cancelled"])
async def test_payment_not_completed_is_409(status):
    conn = Conn(_payment(status))
    with pytest.raises(HTTPException) as exc:
        await create_payment_refund(Ctx(conn), PAY, _body(), MANAGER)
    assert exc.value.status_code == 409
    assert conn.inserted is None


@pytest.mark.asyncio
async def test_refunds_cannot_exceed_the_payment():
    conn = Conn(_payment(amount="100"), refunded="70")
    with pytest.raises(HTTPException) as exc:
        await create_payment_refund(Ctx(conn), PAY, _body("30.01"), MANAGER)
    assert exc.value.status_code == 409
    assert exc.value.detail == "Refund exceeds the payment amount"
    assert conn.inserted is None


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_refund_amount_must_be_positive(amount):
    with pytest.raises(ValidationError):
        PaymentRefundCreate(amount=Decimal(amount))


@pytest.mark.asyncio
async def test_list_refunds_for_a_payment():
    conn = Conn(_payment())
    out = await list_payment_refunds(Ctx(conn), PAY, MANAGER)
    assert out == [{"id": UUID(int=77), "amount": Decimal("5")}]
    assert "ORDER BY created_at" in conn.sql[1]


@pytest.mark.asyncio
async def test_list_refunds_for_unknown_payment_is_404():
    with pytest.raises(HTTPException) as exc:
        await list_payment_refunds(Ctx(Conn(None)), PAY, MANAGER)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_credit_note_must_belong_to_the_invoice():
    conn = Conn(_payment(), credit_note_found=False)
    body = PaymentRefundCreate(amount=Decimal("10"), credit_note_id=CN)
    with pytest.raises(HTTPException) as exc:
        await create_payment_refund(Ctx(conn), PAY, body, MANAGER)
    assert exc.value.status_code == 400
    assert conn.inserted is None


@pytest.mark.asyncio
async def test_refund_links_a_credit_note_of_the_same_invoice():
    conn = Conn(_payment())
    body = PaymentRefundCreate(amount=Decimal("10"), credit_note_id=CN)
    await create_payment_refund(Ctx(conn), PAY, body, MANAGER)
    assert conn.inserted[6] == CN
