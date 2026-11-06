from contextlib import asynccontextmanager

from routers.storefront import storefront_products


class CapturingConn:
    def __init__(self):
        self.sql = []

    async def fetchval(self, sql, *args):
        self.sql.append(sql)
        return 0

    async def fetch(self, sql, *args):
        self.sql.append(sql)
        return []


class FakeCtx:
    subdomain = "acme"

    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def transaction(self):
        yield self.conn


async def test_storefront_catalog_filters_on_marketplace_enabled():
    conn = CapturingConn()
    result = await storefront_products(FakeCtx(conn), q="tea", limit=10, offset=0)

    assert result.total == 0
    assert len(conn.sql) == 2
    for sql in conn.sql:
        assert "p.marketplace_enabled = true" in sql
