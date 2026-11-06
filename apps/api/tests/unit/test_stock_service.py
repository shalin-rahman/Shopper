from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException

from services.stock import change_stock, lock_levels, main_branch_id, record_movement, return_items

TENANT = UUID(int=9)
BRANCH = UUID(int=10)
P1, P2 = UUID(int=1), UUID(int=2)


class Ctx:
    tenant_id = TENANT


class Conn:
    def __init__(self, main=BRANCH, levels=None, update_hits=True):
        self.main = main
        self.levels = levels or {}
        self.update_hits = update_hits
        self.calls = []

    def _log(self, sql, args):
        self.calls.append((" ".join(sql.split()), args))

    async def fetchval(self, sql, *args):
        self._log(sql, args)
        if "FROM tenant_data.branches" in sql:
            return self.main
        if "UPDATE tenant_data.stock_levels" in sql:
            return Decimal("1") if self.update_hits else None
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        self._log(sql, args)
        return [{"product_id": p, "quantity": q} for p, q in self.levels.items()]

    async def fetchrow(self, sql, *args):
        self._log(sql, args)
        return {"id": UUID(int=99), "branch_id": args[1]}

    async def execute(self, sql, *args):
        self._log(sql, args)


@pytest.mark.asyncio
async def test_main_branch_id_returns_the_main_branch():
    assert await main_branch_id(Conn()) == BRANCH


@pytest.mark.asyncio
async def test_main_branch_id_raises_when_tenant_has_none():
    with pytest.raises(HTTPException) as exc:
        await main_branch_id(Conn(main=None))
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_lock_levels_locks_in_product_order_and_fills_missing_with_zero():
    conn = Conn(levels={P2: Decimal("4")})

    levels = await lock_levels(conn, BRANCH, [P2, P1, P2])

    (sql, args), = conn.calls
    assert "FOR UPDATE" in sql and "ORDER BY product_id" in sql
    assert args == (BRANCH, [P1, P2])
    assert levels == {P1: Decimal("0"), P2: Decimal("4")}


@pytest.mark.asyncio
async def test_adding_stock_upserts():
    conn = Conn()

    await change_stock(conn, Ctx(), BRANCH, P1, Decimal("3"))

    (sql, args), = conn.calls
    assert "INSERT INTO tenant_data.stock_levels" in sql
    assert "ON CONFLICT (branch_id, product_id) DO UPDATE SET quantity = tenant_data.stock_levels.quantity + EXCLUDED.quantity" in sql
    assert args == (TENANT, BRANCH, P1, Decimal("3"))


@pytest.mark.asyncio
async def test_taking_more_than_the_branch_holds_is_409():
    conn = Conn(update_hits=False)

    with pytest.raises(HTTPException) as exc:
        await change_stock(conn, Ctx(), BRANCH, P1, Decimal("-3"))

    assert exc.value.status_code == 409
    assert exc.value.detail == "Insufficient stock at branch"
    (sql, _), = conn.calls
    assert "quantity + $3 >= 0" in sql


@pytest.mark.asyncio
async def test_record_movement_writes_nothing_when_stock_is_short():
    conn = Conn(update_hits=False)

    with pytest.raises(HTTPException):
        await record_movement(conn, Ctx(), BRANCH, P1, "out", Decimal("2"), "sale", None, "x")

    assert not any("stock_transactions" in sql for sql, _ in conn.calls)


@pytest.mark.asyncio
async def test_transfer_out_carries_branch_and_takes_stock():
    conn = Conn()

    row = await record_movement(conn, Ctx(), BRANCH, P1, "transfer_out", Decimal("2"),
                                "transfer", None, "to B", reason_code="branch_transfer")

    (update_sql, update_args), (insert_sql, insert_args) = conn.calls
    assert update_args == (BRANCH, P1, Decimal("-2"))
    assert "INSERT INTO tenant_data.stock_transactions" in insert_sql and "branch_id" in insert_sql
    assert insert_args[:5] == (TENANT, BRANCH, P1, "transfer_out", Decimal("2"))
    assert row["branch_id"] == BRANCH


@pytest.mark.asyncio
@pytest.mark.parametrize("kind, qty, delta", [
    ("in", "2", "2"), ("receive", "2", "2"), ("return_in", "2", "2"),
    ("gift_in", "2", "2"), ("transfer_in", "2", "2"),
    ("out", "2", "-2"), ("damage", "2", "-2"), ("expired", "2", "-2"),
    ("adjustment", "-2", "-2"), ("adjustment", "2", "2"),
])
async def test_movement_sign_follows_type(kind, qty, delta):
    conn = Conn()

    await record_movement(conn, Ctx(), BRANCH, P1, kind, Decimal(qty), "manual", None, None)

    assert conn.calls[0][1][-1] == Decimal(delta)


def test_return_items_merges_repeats_and_sorts_by_product():
    items = [{"product_id": str(P2), "qty": "1"}, {"product_id": str(P1), "qty": 2},
             {"product_id": str(P2), "qty": "1.5"}]

    assert return_items(items) == [(P1, Decimal("2")), (P2, Decimal("2.5"))]


@pytest.mark.parametrize("item", [
    {"product_id": "nope", "qty": "1"}, {"qty": "1"}, {"product_id": str(P1)},
    {"product_id": str(P1), "qty": "abc"}, {"product_id": str(P1), "qty": "NaN"},
    {"product_id": str(P1), "qty": "0"}, {"product_id": str(P1), "qty": "-1"},
])
def test_return_items_rejects_bad_items_with_400(item):
    with pytest.raises(HTTPException) as exc:
        return_items([item])
    assert exc.value.status_code == 400
