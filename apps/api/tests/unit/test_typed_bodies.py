"""Money and staff endpoints reject bad bodies with 422 and enforce roles (decision D2)."""

from decimal import Decimal
from uuid import UUID

import asyncpg
import pytest
from fastapi import HTTPException

from conftest import _make_token
from routers.accounts import transfer_funds
from routers.expenses import create_expense
from routers.staff import create_staff
from schemas import AccountTransferCreate, ExpenseCreate, StaffCreate

ADMIN = {"uid": str(UUID(int=0)), "role": "admin", "tid": "t"}
TRANSFER = {"from_account_code": "CASH", "to_account_code": "BANK", "amount": "100.50"}
SUPPLIER_PAYMENT = {
    "supplier_id": str(UUID(int=1)),
    "payment_no": "SP-1",
    "amount": "10",
    "payment_method": "cash",
}


def _headers(role):
    return {"X-Shopper-Tenant": "demo", "Authorization": f"Bearer {_make_token(role)}"}


class Conn:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    async def fetchrow(self, sql, *args):
        if self.error:
            raise self.error
        self.calls.append(("fetchrow", sql, args))
        if "FROM tenant_data.accounts" in sql:
            return {"id": UUID(int=len(self.calls))}
        return {"id": UUID(int=5), "amount": args[2], "created_at": None}

    async def fetchval(self, sql, *args):
        self.calls.append(("fetchval", sql, args))
        return UUID(int=8)

    async def execute(self, sql, *args):
        self.calls.append(("execute", sql, args))


class Tx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class Ctx:
    tenant_id = UUID(int=9)

    def __init__(self, conn):
        self.conn = conn

    def transaction(self):
        return Tx(self.conn)


@pytest.mark.parametrize(
    "body",
    [
        {**TRANSFER, "amount": "abc"},
        {**TRANSFER, "amount": "0"},
        {**TRANSFER, "amount": "1.005"},
        {**TRANSFER, "to_account_code": "CASH"},
        {"to_account_code": "BANK", "amount": "5"},
    ],
)
def test_bad_transfer_is_422(client, body):
    r = client.post("/v1/tenant/accounts/transfer", json=body, headers=_headers("accountant"))
    assert r.status_code == 422


def test_cashier_cannot_transfer(client):
    r = client.post("/v1/tenant/accounts/transfer", json=TRANSFER, headers=_headers("cashier"))
    assert r.status_code == 403


@pytest.mark.parametrize("role", ["accountant", "manager", "admin"])
def test_money_roles_pass_the_role_check(client, role):
    # A bad body reaching validation shows the role check let the caller through.
    r = client.post("/v1/tenant/accounts/transfer", json={}, headers=_headers(role))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_transfer_writes_both_ledger_sides():
    conn = Conn()
    out = await transfer_funds(Ctx(conn), AccountTransferCreate(**TRANSFER), ADMIN)
    assert out == {"status": "success", "transfer_id": str(UUID(int=8))}
    ledger = [c[2] for c in conn.calls if c[0] == "execute"]
    assert [(a[1], a[2]) for a in ledger] == [("CASH", Decimal("100.50")), ("BANK", Decimal("100.50"))]


def test_supplier_payment_cashier_is_403(client):
    r = client.post("/v1/tenant/procurement/payments", json=SUPPLIER_PAYMENT, headers=_headers("cashier"))
    assert r.status_code == 403


def test_supplier_payment_accountant_passes_role_check(client):
    r = client.post("/v1/tenant/procurement/payments", json={}, headers=_headers("accountant"))
    assert r.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"category_id": "not-a-uuid", "amount": "10"},
        {"category_id": str(UUID(int=1)), "amount": "-1"},
        {"category_id": str(UUID(int=1))},
    ],
)
def test_bad_expense_is_422(client, body):
    r = client.post("/v1/tenant/expenses", json=body, headers=_headers("cashier"))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_expense_with_unknown_category_is_404():
    conn = Conn(error=asyncpg.ForeignKeyViolationError("fk"))
    body = ExpenseCreate(category_id=UUID(int=1), amount="10")
    with pytest.raises(HTTPException) as exc:
        await create_expense(Ctx(conn), body, ADMIN)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_expense_without_description_uses_default_ledger_text():
    conn = Conn()
    await create_expense(Ctx(conn), ExpenseCreate(category_id=UUID(int=1), amount="10"), ADMIN)
    ledger = [c[2] for c in conn.calls if c[0] == "execute"]
    assert ledger[0][2] == "Business Expense"


@pytest.mark.parametrize(
    "body",
    [
        {"username": "rina", "role": "cashier"},
        {"username": "rina", "password": "pw-123456", "role": "owner"},
        {"username": "rina", "password": "short"},
        {"username": "ri na", "password": "pw-123456"},
        {"username": "rina", "password": "pw-123456", "branch_id": "not-a-uuid"},
    ],
)
def test_bad_staff_body_is_422(client, body):
    r = client.post("/v1/tenant/staff", json=body, headers=_headers("admin"))
    assert r.status_code == 422


def test_manager_cannot_create_staff(client):
    body = {"username": "rina", "password": "pw-123456"}
    r = client.post("/v1/tenant/staff", json=body, headers=_headers("manager"))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_username_is_409():
    conn = Conn(error=asyncpg.UniqueViolationError("dup"))
    with pytest.raises(HTTPException) as exc:
        await create_staff(Ctx(conn), StaffCreate(username="rina", password="pw-123456"), ADMIN)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_staff_role_defaults_to_cashier():
    conn = Conn()
    await create_staff(Ctx(conn), StaffCreate(username="rina", password="pw-123456"), ADMIN)
    args = conn.calls[0][2]
    assert args[4] == "cashier"
    assert args[2] != "pw-123456"
