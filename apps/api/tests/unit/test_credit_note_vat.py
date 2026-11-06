from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from routers.invoices import _restock_at_sale_cost, _write_credit_note_vat_lines, create_sales_return
from routers.reports import business_analytics_report
from schemas import SalesReturnCreate
from tests.unit.stock_fake import MAIN_BRANCH, StockLevels

TENANT = UUID("44444444-4444-4444-8444-444444444444")
INVOICE = UUID("66666666-6666-4666-8666-666666666666")
NOTE = UUID("77777777-7777-4777-8777-777777777777")
P1 = UUID("00000000-0000-0000-0000-000000000001")
P2 = UUID("00000000-0000-0000-0000-000000000002")
SHOP = UUID("00000000-0000-0000-0000-0000000000b2")
MIGRATION = (
    Path(__file__).resolve().parents[4] / "database" / "migrations" / "028_credit_note_vat.sql"
).read_text(encoding="utf-8")


def _sale_branch_query(sql):
    return "SELECT branch_id FROM tenant_data.stock_transactions" in " ".join(sql.split())


class Conn:
    def __init__(self, sale_cost=None, wac=Decimal("0"), sale_branch=None):
        self.sale_cost = sale_cost
        self.wac = wac
        self.sale_branch = sale_branch
        self.stock = StockLevels(branches=(MAIN_BRANCH, SHOP))
        self.executed = []
        self.fetchval_sql = []
        self.fetch_sql = []

    async def fetchrow(self, sql, *args):
        assert "INSERT INTO tenant_data.stock_transactions" in sql, sql
        self.executed.append((" ".join(sql.split()), args))
        return {"id": UUID(int=7)}

    async def fetchval(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.fetchval(sql, *args)
        if _sale_branch_query(sql):
            return self.sale_branch
        self.fetchval_sql.append(" ".join(sql.split()))
        if "FROM tenant_data.stock_transactions" in sql and "reference_id" in sql:
            return self.sale_cost
        if "wac_cost FROM tenant_data.products" in sql:
            return self.wac
        return Decimal("0")

    async def fetch(self, sql, *args):
        self.fetch_sql.append(" ".join(sql.split()))
        return []

    async def execute(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.execute(sql, *args)
        self.executed.append((" ".join(sql.split()), args))


class Ctx:
    tenant_id = TENANT

    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def transaction(self):
        yield self.conn


@pytest.mark.asyncio
async def test_credit_note_writes_negative_6_7_lines():
    conn = Conn()
    invoice = {"invoice_no": "INV-1", "buyer_name_en": "Rahim"}
    allocations = [{
        "product_id": P1,
        "qty": Decimal("2"),
        "taxable_amount": Decimal("200"),
        "vat_amount": Decimal("20"),
        "discount_amount": Decimal("5"),
        "total_amount": Decimal("215"),
    }]

    await _write_credit_note_vat_lines(conn, Ctx(conn), "CN-1", invoice, allocations)

    (sql, args), = conn.executed
    assert "INSERT INTO tenant_data.vat_sales_register_lines" in sql and "'6.7'" in sql
    # args: tenant, note_no, date, buyer, description, qty, taxable, vat, discount, total
    assert args[1] == "CN-1" and args[3] == "Rahim"
    assert "INV-1" in args[4]
    assert args[5:] == (Decimal("-2"), Decimal("-200"), Decimal("-20"), Decimal("-5"), Decimal("-215"))


@pytest.mark.asyncio
async def test_restock_uses_the_cost_the_sale_went_out_at():
    conn = Conn(sale_cost=Decimal("42.5"), wac=Decimal("99"))

    await _restock_at_sale_cost(conn, Ctx(conn), INVOICE, P1, Decimal("2"), "return", NOTE, "Sales Return: CN-1")

    stock = [args for sql, args in conn.executed if "stock_transactions" in sql]
    assert stock == [(TENANT, MAIN_BRANCH, P1, "in", Decimal("2"), Decimal("42.5"),
                      "return", NOTE, "Sales Return: CN-1", None)]
    assert conn.stock.at(P1) == Decimal("2")


@pytest.mark.asyncio
async def test_restock_goes_back_to_the_branch_the_sale_left():
    conn = Conn(sale_cost=Decimal("10"), sale_branch=SHOP)

    await _restock_at_sale_cost(conn, Ctx(conn), INVOICE, P1, Decimal("2"), "return", NOTE, "x")

    assert conn.stock.at(P1, SHOP) == Decimal("2")
    assert conn.stock.at(P1) == Decimal("0")


@pytest.mark.asyncio
async def test_restock_falls_back_to_average_cost():
    conn = Conn(sale_cost=None, wac=Decimal("12"))

    await _restock_at_sale_cost(conn, Ctx(conn), INVOICE, P1, Decimal("1"), "return", NOTE, "x")

    stock = [args for sql, args in conn.executed if "stock_transactions" in sql]
    assert stock[0][5] == Decimal("12")


@pytest.mark.asyncio
async def test_cogs_takes_out_returned_and_cancelled_goods():
    conn = Conn()

    await business_analytics_report(Ctx(conn), {})

    cogs_sql = conn.fetchval_sql[0]
    assert "transaction_type = 'out' AND reference_type = 'sale'" in cogs_sql
    assert "transaction_type = 'in' AND reference_type IN ('return', 'sale_cancel')" in cogs_sql
    assert "ELSE -quantity * COALESCE(unit_cost, 0)" in cogs_sql


@pytest.mark.asyncio
async def test_eoq_demand_takes_out_returned_and_cancelled_goods():
    conn = Conn()

    await business_analytics_report(Ctx(conn), {})

    (demand_sql,) = conn.fetch_sql
    assert "st.transaction_type = 'out' AND st.reference_type = 'sale'" in demand_sql
    assert "st.transaction_type = 'in' AND st.reference_type IN ('return', 'sale_cancel')" in demand_sql
    assert "GREATEST(" in demand_sql


def test_028_allows_form_6_7_and_keeps_old_forms():
    assert "DROP CONSTRAINT IF EXISTS vat_sales_register_lines_mushak_form_check" in MIGRATION
    assert "CHECK (mushak_form IN ('6.1', '6.2', '6.3', '6.6', '6.7'))" in MIGRATION


class ReturnConn:
    """Drives create_sales_return on an invoice with one line each of P1 and P2."""

    def __init__(self, amount_paid="0", discount="0"):
        self.invoice = {
            "id": INVOICE, "invoice_no": "INV-1", "buyer_name_en": "Rahim",
            "total_amount": Decimal("330") - Decimal(discount), "amount_paid": Decimal(amount_paid),
            "discount": Decimal(discount), "status": "issued",
        }
        self.executed = []
        self.locked = []
        self.stock = StockLevels()

    async def fetchrow(self, sql, *args):
        if "INSERT INTO tenant_data.stock_transactions" in sql:
            self.executed.append((" ".join(sql.split()), args))
            return {"id": UUID(int=7)}
        if "FROM tenant_data.invoices" in sql:
            return self.invoice
        if "INSERT INTO tenant_data.credit_notes" in sql:
            self.executed.append((" ".join(sql.split()), args))
            return {
                "id": NOTE, "note_no": args[2], "invoice_id": INVOICE, "reason": args[3],
                "total_adjustment": args[7], "discount_amount": args[6],
                "created_at": datetime(2026, 10, 23, tzinfo=timezone.utc),
            }
        raise AssertionError(sql)

    async def fetchval(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.fetchval(sql, *args)
        if _sale_branch_query(sql):
            return MAIN_BRANCH
        if "FROM tenant_data.stock_transactions" in sql:
            return Decimal("40")
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        if "FROM tenant_data.credit_note_lines" in sql:
            return []
        if "FROM tenant_data.invoice_lines" in sql:
            lines = [
                {"id": UUID(int=p.int + 100), "product_id": p, "qty": Decimal("1"),
                 "unit_price": Decimal("200") if p == P1 else Decimal("100"), "vat_rate_pct": Decimal("10")}
                for p in (P1, P2)
            ]
            if len(args) == 1:
                # Every line, for the discount split; it must match issue's order.
                assert "ORDER BY id" in sql
                return lines
            return [line for line in lines if line["product_id"] == args[1]]
        if "FROM tenant_data.products" in sql:
            assert "ORDER BY id" in sql and "FOR UPDATE" in sql
            assert not self.executed, "products must be locked before any write"
            self.locked.append(list(args[0]))
            return []
        raise AssertionError(sql)

    async def execute(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.execute(sql, *args)
        self.executed.append((" ".join(sql.split()), args))


def _return_body(items=None):
    return SalesReturnCreate(
        invoice_id=INVOICE, reason="damaged",
        items=items or [{"product_id": P2, "qty": "1"}, {"product_id": P1, "qty": "1"}],
    )


@pytest.mark.asyncio
async def test_return_locks_products_in_id_order_before_writing():
    conn = ReturnConn()

    await create_sales_return(Ctx(conn), _return_body(), {})

    assert conn.locked == [[P1, P2]]


@pytest.mark.asyncio
async def test_return_on_unpaid_invoice_keeps_its_status():
    conn = ReturnConn(amount_paid="0")

    await create_sales_return(Ctx(conn), _return_body(), {})

    (update,) = [sql for sql, _ in conn.executed if sql.startswith("UPDATE tenant_data.invoices")]
    # Unpaid stays issued, even after a full return; only a payment moves it on.
    assert "WHEN amount_paid = 0 THEN status" in update
    assert update.index("WHEN amount_paid = 0") < update.index("THEN 'paid'")


@pytest.mark.asyncio
@pytest.mark.parametrize("items, expected", [
    ([{"product_id": P2, "qty": "1"}], Decimal("10")),
    (None, Decimal("30")),
])
async def test_return_gives_back_the_discount_issue_put_on_each_line(items, expected):
    # Issue split 30 by ex-VAT subtotal: P1 (200) took 20, P2 (100) took 10.
    conn = ReturnConn(discount="30")

    await create_sales_return(Ctx(conn), _return_body(items), {})

    (args,) = [a for sql, a in conn.executed if sql.startswith("INSERT INTO tenant_data.credit_notes")]
    assert args[6] == expected
