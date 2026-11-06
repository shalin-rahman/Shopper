"""Branch-to-branch transfer moves stock between stock_levels rows and logs both sides."""

from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from routers.inventory import StockTransferRequest, create_stock_transfer, get_mushak_6_5_pdf
from tests.unit.stock_fake import MAIN_BRANCH, StockLevels

TENANT = UUID(int=9)
P = UUID(int=1)
SHOP = UUID("00000000-0000-0000-0000-0000000000b2")
GONE = UUID("00000000-0000-0000-0000-0000000000b3")
STAFF = UUID(int=50)
ADMIN = {"uid": str(UUID(int=0)), "role": "admin", "tid": "t"}
CASHIER = {"uid": str(STAFF), "role": "cashier", "tid": "t"}


def _flat(sql):
    return " ".join(sql.split())


class Conn:
    def __init__(self, levels):
        self.stock = StockLevels(levels, branches=(MAIN_BRANCH, SHOP))
        self.sql = []
        self.movements = []

    async def fetchrow(self, sql, *args):
        self.sql.append(_flat(sql))
        if "INSERT INTO tenant_data.stock_transactions" in sql:
            self.movements.append(args)
            return {"id": UUID(int=100 + len(self.movements))}
        if "FROM tenant_data.staff" in sql:
            # The cashier has no home branch set, so works at the main branch.
            return {"branch_id": None} if args == (STAFF,) else None
        if "FROM tenant_data.products" in sql:
            # args are (product_id, sku); the route sends exactly one of them.
            return {"id": P} if P in args or "S1" in args else None
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        return await self.stock.fetch(sql, *args)

    async def fetchval(self, sql, *args):
        return await self.stock.fetchval(sql, *args)

    async def execute(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.execute(sql, *args)
        self.sql.append(_flat(sql))


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


def _body(qty="4", to=SHOP, frm=None, sku="S1"):
    return StockTransferRequest(sku=sku, qty=Decimal(qty), to_branch_id=to, from_branch_id=frm)


@pytest.mark.asyncio
async def test_transfer_moves_stock_and_logs_both_sides():
    conn = Conn({P: 10})

    out = await create_stock_transfer(Ctx(conn), _body("4"), ADMIN)

    assert conn.stock.at(P) == Decimal("6")
    assert conn.stock.at(P, SHOP) == Decimal("4")
    sent, received = conn.movements
    assert sent[1:5] == (MAIN_BRANCH, P, "transfer_out", Decimal("4"))
    assert received[1:5] == (SHOP, P, "transfer_in", Decimal("4"))
    assert sent[6] == received[6] == "transfer"
    assert sent[9] == received[9] == "branch_transfer"
    assert out == {"id": UUID(int=101), "mushak_form": "6.5", "status": "recorded"}
    assert not any("stock_quantity" in sql for sql in conn.sql)


@pytest.mark.asyncio
async def test_transfer_from_a_named_branch():
    conn = Conn({(SHOP, P): 5})

    await create_stock_transfer(Ctx(conn), _body("5", to=MAIN_BRANCH, frm=SHOP), ADMIN)

    assert conn.stock.at(P, SHOP) == Decimal("0")
    assert conn.stock.at(P) == Decimal("5")


@pytest.mark.asyncio
async def test_transfer_locks_both_branches_in_id_order():
    conn = Conn({(SHOP, P): 5})

    await create_stock_transfer(Ctx(conn), _body("1", to=MAIN_BRANCH, frm=SHOP), ADMIN)

    assert [branch for branch, _ in conn.stock.locked] == sorted([MAIN_BRANCH, SHOP])


@pytest.mark.asyncio
async def test_transfer_to_the_same_branch_is_400():
    conn = Conn({P: 10})

    with pytest.raises(HTTPException) as exc:
        await create_stock_transfer(Ctx(conn), _body("1", to=MAIN_BRANCH), ADMIN)

    assert exc.value.status_code == 400
    assert conn.movements == []


@pytest.mark.asyncio
async def test_transfer_to_an_unknown_branch_is_400():
    conn = Conn({P: 10})

    with pytest.raises(HTTPException) as exc:
        await create_stock_transfer(Ctx(conn), _body("1", to=GONE), ADMIN)

    assert exc.value.status_code == 400
    assert conn.stock.at(P) == Decimal("10")


@pytest.mark.asyncio
async def test_transfer_more_than_the_source_holds_is_409_with_no_writes():
    conn = Conn({P: 3})

    with pytest.raises(HTTPException) as exc:
        await create_stock_transfer(Ctx(conn), _body("4"), ADMIN)

    assert exc.value.status_code == 409
    assert conn.movements == []
    assert conn.stock.at(P) == Decimal("3")
    assert conn.stock.at(P, SHOP) == Decimal("0")


@pytest.mark.asyncio
async def test_transfer_of_unknown_sku_is_404():
    conn = Conn({P: 3})

    with pytest.raises(HTTPException) as exc:
        await create_stock_transfer(Ctx(conn), _body("1", sku="NOPE"), ADMIN)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_transfer_by_product_id():
    conn = Conn({P: 10})

    await create_stock_transfer(
        Ctx(conn), StockTransferRequest(product_id=P, qty=Decimal("2"), to_branch_id=SHOP), ADMIN
    )

    assert conn.stock.at(P, SHOP) == Decimal("2")
    lookup = next(sql for sql in conn.sql if "FROM tenant_data.products" in sql)
    assert "is_active" in lookup and "FOR UPDATE" in lookup


@pytest.mark.asyncio
async def test_transfer_of_unknown_product_id_is_404():
    conn = Conn({P: 10})

    with pytest.raises(HTTPException) as exc:
        await create_stock_transfer(
            Ctx(conn), StockTransferRequest(product_id=UUID(int=99), qty=Decimal("1"), to_branch_id=SHOP), ADMIN
        )

    assert exc.value.status_code == 404


@pytest.mark.parametrize("keys", [{}, {"sku": "S1", "product_id": P}, {"sku": "  "}])
def test_transfer_needs_exactly_one_of_sku_or_product_id(keys):
    with pytest.raises(ValidationError):
        StockTransferRequest(qty=Decimal("1"), to_branch_id=SHOP, **keys)


class PdfConn:
    def __init__(self):
        self.sql = []

    async def fetchrow(self, sql, *args):
        self.sql.append(_flat(sql))
        return None


@pytest.mark.asyncio
async def test_mushak_6_5_only_renders_the_sending_side_of_a_transfer():
    # A sale or the transfer_in row must not print as a transfer challan.
    conn = PdfConn()

    with pytest.raises(HTTPException) as exc:
        await get_mushak_6_5_pdf(Ctx(conn), UUID(int=101), None)

    assert exc.value.status_code == 404
    (sql,) = conn.sql
    # 'out' with reference_type 'transfer' is how transfers were stored before branches.
    assert "tx.reference_type = 'transfer' AND tx.transaction_type IN ('transfer_out', 'out')" in sql


@pytest.mark.asyncio
async def test_cashier_cannot_send_from_another_branch():
    conn = Conn({(SHOP, P): 10})

    with pytest.raises(HTTPException) as exc:
        await create_stock_transfer(Ctx(conn), _body("1", to=MAIN_BRANCH, frm=SHOP), CASHIER)

    assert exc.value.status_code == 403
    assert conn.movements == []


@pytest.mark.asyncio
async def test_cashier_sends_from_own_branch():
    conn = Conn({P: 10})

    await create_stock_transfer(Ctx(conn), _body("4"), CASHIER)

    assert conn.stock.at(P, SHOP) == Decimal("4")
