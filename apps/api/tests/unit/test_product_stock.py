"""Product create and update move stock through services.stock, not by writing products.stock_quantity."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException

from core.dependencies import BranchChoice
from routers.products import create_product, update_product
from schemas import ProductCreate, ProductUpdate
from tests.unit.stock_fake import MAIN_BRANCH, StockLevels

TENANT = UUID(int=9)
P = UUID(int=1)
SHOP = UUID(int=0xB2)


def _flat(sql):
    return " ".join(sql.split())


class Settings:
    storefront_public_base_url = "https://shop.test"


class Conn:
    def __init__(self, levels=None):
        self.stock = StockLevels(levels or {}, branches=(MAIN_BRANCH, SHOP))
        self.sql = []
        self.movements = []

    def total(self):
        return sum((q for (_, p), q in self.stock.levels.items() if p == P), Decimal("0"))

    def _product(self, stock_quantity):
        now = datetime.now(timezone.utc)
        return {
            "id": P, "tenant_id": TENANT, "category_id": None, "sku": "S1", "name_en": "Rice",
            "name_bn": "Rice", "description_en": None, "description_bn": None, "unit": "pcs",
            "buy_price": Decimal("10"), "sell_price": Decimal("12"), "mrp": None,
            "vat_rate_pct": Decimal("0"), "barcode": None, "qr_payload": None,
            "stock_quantity": stock_quantity, "is_active": True, "marketplace_enabled": False,
            "created_at": now, "updated_at": now,
        }

    async def fetchrow(self, sql, *args):
        self.sql.append(_flat(sql))
        if "INSERT INTO tenant_data.stock_transactions" in sql:
            self.movements.append(args)
            return {"id": UUID(int=7)}
        if "INSERT INTO tenant_data.products" in sql:
            return self._product(args[14])
        if "SELECT stock_quantity, buy_price" in sql:
            return {"stock_quantity": self.total(), "buy_price": Decimal("10")}
        if "UPDATE tenant_data.products" in sql:
            return self._product(self.total())
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        return await self.stock.fetch(sql, *args)

    async def fetchval(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.fetchval(sql, *args)
        self.sql.append(_flat(sql))
        if "SELECT stock_quantity FROM tenant_data.products" in sql:
            return self.total()
        raise AssertionError(sql)

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
    subdomain = "demo"

    def __init__(self, conn):
        self.conn = conn

    def transaction(self):
        return Tx(self.conn)


def _create(qty):
    return ProductCreate(sku="S1", name_en="Rice", name_bn="Rice", buy_price=Decimal("10"), stock_quantity=qty)


def _writes_stock_quantity(sql):
    if sql.startswith("INSERT INTO tenant_data.products"):
        return False
    return "stock_quantity =" in sql or "stock_quantity=" in sql


@pytest.mark.asyncio
async def test_create_inserts_zero_then_records_opening_stock_at_the_branch():
    conn = Conn()

    out = await create_product(Ctx(conn), _create(Decimal("5")), Settings(), None, BranchChoice(None))

    (args,) = conn.movements
    assert args[1:6] == (MAIN_BRANCH, P, "in", Decimal("5"), Decimal("10"))
    assert conn.stock.at(P) == Decimal("5")
    assert out.stock_quantity == Decimal("5")


@pytest.mark.asyncio
async def test_create_does_not_put_the_opening_qty_on_the_product_row():
    conn = Conn()
    seen = []
    original = conn.fetchrow

    async def spy(sql, *args):
        if "INSERT INTO tenant_data.products" in sql:
            seen.append(args[14])
        return await original(sql, *args)

    conn.fetchrow = spy
    await create_product(Ctx(conn), _create(Decimal("5")), Settings(), None, BranchChoice(None))

    # The trigger sets the total from stock_levels; a non-zero insert would be overwritten or doubled.
    assert seen == [Decimal("0")]


@pytest.mark.asyncio
async def test_create_with_no_stock_records_no_movement():
    conn = Conn()

    out = await create_product(Ctx(conn), _create(Decimal("0")), Settings(), None, BranchChoice(None))

    assert conn.movements == []
    assert out.stock_quantity == Decimal("0")


@pytest.mark.asyncio
async def test_update_lowering_the_total_takes_the_difference_from_the_branch():
    conn = Conn({P: 10})

    out = await update_product(Ctx(conn), P, ProductUpdate(stock_quantity=Decimal("7")), None, BranchChoice(None))

    (args,) = conn.movements
    assert args[1:5] == (MAIN_BRANCH, P, "out", Decimal("3"))
    assert args[9] == "adjustment"
    assert conn.stock.at(P) == Decimal("7")
    assert out.stock_quantity == Decimal("7")
    assert not any(_writes_stock_quantity(sql) for sql in conn.sql)


@pytest.mark.asyncio
async def test_update_raising_the_total_adds_at_the_chosen_branch():
    conn = Conn({(SHOP, P): 10})

    await update_product(Ctx(conn), P, ProductUpdate(stock_quantity=Decimal("12")), None, BranchChoice(SHOP))

    assert conn.stock.at(P, SHOP) == Decimal("12")
    assert conn.stock.at(P) == Decimal("0")


@pytest.mark.asyncio
async def test_update_first_stock_at_a_new_branch_is_allowed():
    conn = Conn()

    await update_product(Ctx(conn), P, ProductUpdate(stock_quantity=Decimal("4")), None, BranchChoice(SHOP))

    assert conn.stock.at(P, SHOP) == Decimal("4")


@pytest.mark.parametrize("new_total", [Decimal("5"), Decimal("15")])
@pytest.mark.asyncio
async def test_update_total_when_other_branches_hold_stock_is_409(new_total):
    # Main holds 1 and the shop 9. A new total of 5 or 15 says nothing about which branch changes.
    conn = Conn({(MAIN_BRANCH, P): 1, (SHOP, P): 9})

    with pytest.raises(HTTPException) as exc:
        await update_product(Ctx(conn), P, ProductUpdate(stock_quantity=new_total), None, BranchChoice(None))

    assert exc.value.status_code == 409
    assert "/inventory/adjust" in exc.value.detail
    assert conn.movements == []
    assert conn.stock.at(P) == Decimal("1")
    assert conn.stock.at(P, SHOP) == Decimal("9")


@pytest.mark.asyncio
async def test_update_to_the_same_total_with_stock_at_several_branches_is_fine():
    conn = Conn({(MAIN_BRANCH, P): 1, (SHOP, P): 9})

    await update_product(Ctx(conn), P, ProductUpdate(stock_quantity=Decimal("10")), None, BranchChoice(None))

    assert conn.movements == []


@pytest.mark.asyncio
async def test_update_without_stock_field_moves_nothing():
    conn = Conn({P: 10})

    await update_product(Ctx(conn), P, ProductUpdate(sell_price=Decimal("15")), None, BranchChoice(None))

    assert conn.movements == []
    assert conn.stock.at(P) == Decimal("10")
