from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException

from core.dependencies import BranchChoice
from routers.inventory import (
    StockAdjustRequest,
    StockReceiveRequest,
    stock_adjust,
    stock_receive,
)
from tests.unit.stock_fake import MAIN_BRANCH, StockLevels

PRODUCT = UUID("00000000-0000-0000-0000-000000000001")


class _FakeConnection:
    def __init__(self, stock_quantity: Decimal = Decimal("5")):
        self.stock = StockLevels({PRODUCT: stock_quantity})
        self.movements = []
        self.product_id = PRODUCT

    @property
    def stock_quantity(self):
        return self.stock.at(PRODUCT)

    async def fetchrow(self, query, *args):
        if "FROM tenant_data.products" in query:
            return {"id": self.product_id}
        if "INSERT INTO tenant_data.stock_transactions" in query:
            self.movements.append(args)
            return {"id": UUID("00000000-0000-0000-0000-000000000002")}
        raise AssertionError(f"Unexpected query: {query}")

    async def fetchval(self, query, *args):
        assert self.stock.handles(query), query
        return await self.stock.fetchval(query, *args)

    async def execute(self, query, *args):
        assert self.stock.handles(query), query
        return await self.stock.execute(query, *args)


class _FakeTenantContext:
    tenant_id = UUID("00000000-0000-0000-0000-000000000010")

    def __init__(self, connection):
        self.connection = connection

    @asynccontextmanager
    async def transaction(self):
        yield self.connection


@pytest.mark.asyncio
async def test_stock_receive_records_tenant_movement_and_updates_quantity():
    connection = _FakeConnection()
    result = await stock_receive(
        _FakeTenantContext(connection),
        StockReceiveRequest(sku="SKU-1", qty=Decimal("3"), unit_cost=Decimal("4")),
        None,
        BranchChoice(None),
    )

    assert result["status"] == "recorded"
    assert connection.stock_quantity == Decimal("8")
    assert connection.movements[0][0] == UUID("00000000-0000-0000-0000-000000000010")
    assert connection.movements[0][1:5] == (MAIN_BRANCH, PRODUCT, "in", Decimal("3"))


@pytest.mark.asyncio
async def test_stock_adjustment_rejects_quantity_above_available_stock():
    connection = _FakeConnection(stock_quantity=Decimal("2"))

    with pytest.raises(HTTPException) as exc:
        await stock_adjust(
            _FakeTenantContext(connection),
            StockAdjustRequest(sku="SKU-1", qty=Decimal("3")),
            None,
            BranchChoice(None),
        )

    assert exc.value.status_code == 409
    assert connection.movements == []
    assert connection.stock_quantity == Decimal("2")
