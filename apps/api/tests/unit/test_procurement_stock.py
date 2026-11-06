"""PO receive and purchase returns move stock at a branch through services.stock."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException

from core.dependencies import BranchChoice
from routers.procurement import receive_po
from routers.suppliers import create_purchase_return as supplier_return
from schemas import PurchaseReturnCreate
from tests.unit.stock_fake import MAIN_BRANCH, StockLevels

TENANT = UUID(int=9)
PO = UUID(int=50)
P1 = UUID(int=1)


def _flat(sql):
    return " ".join(sql.split())


class Conn:
    def __init__(self, levels=None, po_status="draft", returned=None):
        self.stock = StockLevels(levels or {})
        self.po_status = po_status
        self.returned = returned or []
        self.sql = []
        self.movements = []
        self.locked_products = None
        self.debit_notes = []
        self.updates = []

    async def fetchrow(self, sql, *args):
        self.sql.append(_flat(sql))
        if "INSERT INTO tenant_data.stock_transactions" in sql:
            self.movements.append(args)
            return {"id": UUID(int=7)}
        if "FROM tenant_data.purchase_orders" in sql:
            return {"status": self.po_status, "supplier_id": UUID(int=60)}
        if "FROM tenant_data.products" in sql:
            return {"buy_price": Decimal("10"), "vat_rate_pct": Decimal("15")}
        if "INSERT INTO tenant_data.debit_notes" in sql:
            self.debit_notes.append(args)
            return {
                "id": UUID(int=70), "tenant_id": TENANT, "supplier_id": UUID(int=60), "po_id": PO,
                "reference_id": PO, "note_no": "DN-1", "reason": "bad", "total_adjustment": Decimal("0"),
                "adjustment_amount_taxable": Decimal("0"), "adjustment_amount_vat": Decimal("0"),
                "created_at": datetime.now(timezone.utc),
            }
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.fetch(sql, *args)
        self.sql.append(_flat(sql))
        if "FROM tenant_data.products" in sql and "FOR UPDATE" in sql:
            assert self.movements == [], "products must be locked before any stock write"
            self.locked_products = list(args[0])
            return []
        if "FROM tenant_data.po_lines" in sql:
            return [{"product_id": P1, "qty": Decimal("5"), "unit_cost": Decimal("12")}]
        if "FROM tenant_data.stock_transactions" in sql:
            return self.returned
        raise AssertionError(sql)

    async def fetchval(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.fetchval(sql, *args)
        self.sql.append(_flat(sql))
        if "buy_price" in sql:
            return Decimal("10")
        raise AssertionError(sql)

    async def execute(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.execute(sql, *args)
        self.sql.append(_flat(sql))
        self.updates.append(args)


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


def _return_body(qty="2"):
    return PurchaseReturnCreate(po_id=PO, reason="bad", items=[{"product_id": str(P1), "qty": qty}])


@pytest.mark.asyncio
async def test_receive_po_adds_stock_at_the_branch_with_cost():
    conn = Conn()

    await receive_po(Ctx(conn), PO, None, BranchChoice(None))

    assert conn.stock.at(P1) == Decimal("5")
    (args,) = conn.movements
    assert args[1:7] == (MAIN_BRANCH, P1, "in", Decimal("5"), Decimal("12"), "po")
    assert not any("stock_quantity" in sql for sql in conn.sql)


@pytest.mark.asyncio
async def test_receive_po_locks_the_po_so_two_receives_cannot_both_add_stock():
    conn = Conn()

    await receive_po(Ctx(conn), PO, None, BranchChoice(None))

    po_select = next(sql for sql in conn.sql if "FROM tenant_data.purchase_orders" in sql)
    assert "FOR UPDATE" in po_select


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [supplier_return])
async def test_purchase_return_takes_stock_with_positive_qty(handler):
    conn = Conn({P1: 5}, po_status="received")

    await handler(Ctx(conn), _return_body("2"), None, BranchChoice(None))

    assert conn.stock.at(P1) == Decimal("3")
    (args,) = conn.movements
    assert args[1:5] == (MAIN_BRANCH, P1, "out", Decimal("2"))
    assert args[6] == "purchase_return"
    assert not any("stock_quantity" in sql for sql in conn.sql)


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [supplier_return])
async def test_purchase_return_more_than_held_is_409(handler):
    conn = Conn({P1: 1}, po_status="received")

    with pytest.raises(HTTPException) as exc:
        await handler(Ctx(conn), _return_body("2"), None, BranchChoice(None))

    assert exc.value.status_code == 409
    assert conn.movements == []


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [supplier_return])
@pytest.mark.parametrize("qty", ["0", "-3"])
async def test_purchase_return_rejects_non_positive_qty(handler, qty):
    conn = Conn({P1: 5}, po_status="received")

    with pytest.raises(HTTPException) as exc:
        await handler(Ctx(conn), _return_body(qty), None, BranchChoice(None))

    assert exc.value.status_code == 400
    assert conn.stock.at(P1) == Decimal("5")


@pytest.mark.asyncio
async def test_receive_po_reads_lines_in_product_order():
    # Each line updates the product row; a fixed order stops two POs deadlocking.
    conn = Conn()

    await receive_po(Ctx(conn), PO, None, BranchChoice(None))

    lines_select = next(sql for sql in conn.sql if "FROM tenant_data.po_lines" in sql)
    assert "ORDER BY product_id" in lines_select


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [supplier_return])
async def test_purchase_return_locks_products_before_stock(handler):
    # Sales lock the product first, then the stock row. Returns must do the same.
    conn = Conn({P1: 5}, po_status="received")

    await handler(Ctx(conn), _return_body("2"), None, BranchChoice(None))

    assert conn.locked_products == [P1]


@pytest.mark.asyncio
async def test_purchase_return_note_numbers_differ_on_the_same_po_and_day():
    # note_no is unique per tenant. Two returns on one PO on one day must not collide.
    notes = []
    for _ in range(2):
        conn = Conn({P1: 5}, po_status="received")
        await supplier_return(Ctx(conn), _return_body("1"), None, BranchChoice(None))
        notes.append(conn.debit_notes[0][2])

    first, second = notes
    assert first.startswith("DN-") and first != second


@pytest.mark.asyncio
async def test_purchase_return_records_po_and_supplier():
    conn = Conn({P1: 5}, po_status="received")

    await supplier_return(Ctx(conn), _return_body("2"), None, BranchChoice(None))

    insert = next(sql for sql in conn.sql if "INSERT INTO tenant_data.debit_notes" in sql)
    assert "po_id" in insert and "supplier_id" in insert
    args = conn.debit_notes[0]
    assert PO in args and UUID(int=60) in args


@pytest.mark.asyncio
async def test_purchase_return_lowers_the_po_balance_by_the_po_cost_without_vat():
    # The PO total is qty x unit_cost with no VAT, so only that comes off it.
    # The debit note still carries the VAT.
    conn = Conn({P1: 5}, po_status="received")

    await supplier_return(Ctx(conn), _return_body("2"), None, BranchChoice(None))

    po_select = next(sql for sql in conn.sql if "FROM tenant_data.purchase_orders" in sql)
    assert "FOR UPDATE" in po_select
    update = next(sql for sql in conn.sql if sql.startswith("UPDATE tenant_data.purchase_orders"))
    assert "GREATEST(total_amount - $1, 0)" in update
    assert "GREATEST(balance_due - $1, 0)" in update
    # 2 x 12 PO unit cost, not today's buy price of 10.
    assert conn.updates[0][0] == Decimal("24")
    # 24 plus 15% VAT.
    assert conn.debit_notes[0][-1] == Decimal("27.6")


@pytest.mark.asyncio
async def test_purchase_return_needs_a_received_po():
    conn = Conn({P1: 5}, po_status="draft")

    with pytest.raises(HTTPException) as exc:
        await supplier_return(Ctx(conn), _return_body("2"), None, BranchChoice(None))

    assert exc.value.status_code == 400
    assert conn.movements == [] and conn.debit_notes == []


@pytest.mark.asyncio
async def test_purchase_return_rejects_a_product_not_on_the_po():
    other = UUID(int=2)
    conn = Conn({other: 5}, po_status="received")
    body = PurchaseReturnCreate(po_id=PO, reason="bad", items=[{"product_id": str(other), "qty": "1"}])

    with pytest.raises(HTTPException) as exc:
        await supplier_return(Ctx(conn), body, None, BranchChoice(None))

    assert exc.value.status_code == 400
    assert conn.movements == []


@pytest.mark.asyncio
@pytest.mark.parametrize(("earlier", "qty"), [(None, "6"), (Decimal("4"), "2")])
async def test_purchase_return_cannot_exceed_what_the_po_brought_in(earlier, qty):
    # The PO line is 5 units. 6 is too many; so is 2 after 4 already went back.
    returned = [{"product_id": P1, "qty": earlier}] if earlier else []
    conn = Conn({P1: 10}, po_status="received", returned=returned)

    with pytest.raises(HTTPException) as exc:
        await supplier_return(Ctx(conn), _return_body(qty), None, BranchChoice(None))

    assert exc.value.status_code == 400
    assert conn.movements == []


@pytest.mark.asyncio
async def test_purchase_return_allows_the_rest_after_an_earlier_return():
    conn = Conn({P1: 10}, po_status="received", returned=[{"product_id": P1, "qty": Decimal("3")}])

    await supplier_return(Ctx(conn), _return_body("2"), None, BranchChoice(None))

    assert conn.stock.at(P1) == Decimal("8")
