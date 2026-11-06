"""POS sync sends the stock held at the till's branch, not the tenant-wide total."""

from uuid import UUID

import pytest

from routers.pos import pos_sync_data

SHOP = UUID("00000000-0000-0000-0000-0000000000b2")


def _flat(sql):
    return " ".join(sql.split())


class Branch:
    async def resolve(self, conn):
        return SHOP


class Conn:
    def __init__(self):
        self.calls = []

    async def fetch(self, sql, *args):
        self.calls.append((_flat(sql), args))
        if "product_categories" in sql:
            return [{"id": UUID(int=5), "name_en": "Food", "name_bn": None}]
        return [{"id": UUID(int=1), "stock_quantity": 3}]


class Tx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class Ctx:
    def __init__(self, conn):
        self.conn = conn

    def transaction(self):
        return Tx(self.conn)


@pytest.mark.asyncio
async def test_sync_reads_the_branch_stock_level():
    conn = Conn()

    out = await pos_sync_data(Ctx(conn), None, Branch())

    sql, args = next(c for c in conn.calls if "FROM tenant_data.products" in c[0])
    assert "LEFT JOIN tenant_data.stock_levels sl ON sl.product_id = p.id AND sl.branch_id = $1" in sql
    assert "COALESCE(sl.quantity, 0) AS stock_quantity" in sql
    assert "p.stock_quantity" not in sql
    assert args == (SHOP,)
    assert out["branch_id"] == SHOP
    assert out["products"] == [{"id": UUID(int=1), "stock_quantity": 3}]
    assert len(out["categories"]) == 1
