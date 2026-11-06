from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

from routers.reports import _inventory_turnover, mushak_6_10_report


class CapturingConn:
    def __init__(self):
        self.sql = []

    async def fetch(self, sql, *args):
        self.sql.append(sql)
        return []


class FakeCtx:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def transaction(self):
        yield self.conn


def test_turnover_zero_inventory_returns_zero():
    assert _inventory_turnover(Decimal("5000"), Decimal("0")) == Decimal("0")


def test_turnover_normal():
    assert _inventory_turnover(Decimal("1200"), Decimal("300")) == Decimal("4")


async def test_mushak_6_10_sql_includes_walk_in_and_excludes_drafts():
    conn = CapturingConn()
    await mushak_6_10_report(FakeCtx(conn), None, month=3, year=2026)

    sql = conn.sql[0]
    assert "LEFT JOIN tenant_data.customers" in sql
    assert "COALESCE(c.name_en, i.buyer_name_en)" in sql
    assert "i.status NOT IN ('draft', 'cancelled')" in sql


async def test_mushak_6_10_end_date_is_month_end():
    report = await mushak_6_10_report(FakeCtx(CapturingConn()), None, month=2, year=2028)
    assert report.start_date == date(2028, 2, 1)
    assert report.end_date == date(2028, 2, 29)
