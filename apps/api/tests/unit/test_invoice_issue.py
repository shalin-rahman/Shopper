from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException

from core.dependencies import BranchChoice
from routers.invoices import _split_discount, cancel_invoice, issue_invoice
from tests.unit.stock_fake import MAIN_BRANCH, StockLevels

TENANT = UUID("44444444-4444-4444-8444-444444444444")
INVOICE = UUID("66666666-6666-4666-8666-666666666666")
P1 = UUID("00000000-0000-0000-0000-000000000001")
P2 = UUID("00000000-0000-0000-0000-000000000002")


def _invoice(status="draft", amount_paid="0", discount="0"):
    return {
        "id": INVOICE,
        "tenant_id": TENANT,
        "customer_id": None,
        "invoice_no": "INV-1",
        "subtotal": Decimal("300"),
        "discount": Decimal(discount),
        "total_vat": Decimal("30"),
        "total_amount": Decimal("330") - Decimal(discount),
        "amount_paid": Decimal(amount_paid),
        "balance_due": Decimal("330") - Decimal(amount_paid),
        "status": status,
        "notes": None,
        "buyer_name_en": "Rahim",
        "created_at": datetime(2026, 10, 23, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 10, 23, tzinfo=timezone.utc),
    }


def _line(line_id, product_id, qty, unit_price):
    qty, unit_price = Decimal(qty), Decimal(unit_price)
    vat = qty * unit_price / Decimal("10")
    return {
        "id": UUID(int=line_id),
        "invoice_id": INVOICE,
        "product_id": product_id,
        "description": f"Item {line_id}",
        "qty": qty,
        "unit_price": unit_price,
        "vat_rate_pct": Decimal("10"),
        "vat_amount": vat,
        "line_total": qty * unit_price + vat,
    }


LINES = [_line(1, P1, "2", "100"), _line(2, P2, "1", "100")]


class Conn:
    def __init__(self, invoice, lines=LINES, stock=None, credit_notes=0, pending_payments=0):
        self.invoice = invoice
        self.lines = lines
        self.products = stock if stock is not None else {P1: Decimal("5"), P2: Decimal("5")}
        self.stock = StockLevels(self.products)
        self.credit_notes = credit_notes
        self.pending_payments = pending_payments
        self.executed = []
        self.locked = []

    async def fetchrow(self, sql, *args):
        if "INSERT INTO tenant_data.stock_transactions" in sql:
            self.executed.append((" ".join(sql.split()), args))
            return {"id": UUID(int=7)}
        if "FROM tenant_data.invoices" in sql and "FOR UPDATE" in sql:
            return self.invoice
        if sql.lstrip().startswith("UPDATE tenant_data.invoices"):
            self.invoice = {**self.invoice, "status": args[1]}
            return self.invoice
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.fetch(sql, *args)
        if "FROM tenant_data.invoice_lines" in sql:
            return self.lines
        if "FROM tenant_data.products" in sql:
            assert "FOR UPDATE" in sql and "ORDER BY id" in sql
            assert not self.executed, "products must be locked before any write"
            self.locked.append(list(args[0]))
            return [{"id": pid, "is_active": True} for pid in self.products if pid in args[0]]
        raise AssertionError(sql)

    async def fetchval(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.fetchval(sql, *args)
        if "SELECT branch_id FROM tenant_data.stock_transactions" in " ".join(sql.split()):
            return MAIN_BRANCH
        if "FROM tenant_data.credit_notes" in sql:
            return self.credit_notes
        if "FROM tenant_data.payments" in sql:
            assert "status = 'pending'" in sql
            return self.pending_payments
        if "FROM tenant_data.stock_transactions" in sql:
            return Decimal("40")
        raise AssertionError(sql)

    async def execute(self, sql, *args):
        if self.stock.handles(sql):
            return await self.stock.execute(sql, *args)
        self.executed.append((" ".join(sql.split()), args))

    def calls(self, prefix):
        return [args for sql, args in self.executed if sql.startswith(prefix)]


class Ctx:
    tenant_id = TENANT

    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def transaction(self):
        yield self.conn


def test_split_discount_is_proportional_and_sums_exactly():
    parts = _split_discount([Decimal("200"), Decimal("100")], Decimal("10"))
    assert parts == [Decimal("6.6667"), Decimal("3.3333")]
    assert sum(parts) == Decimal("10")
    assert _split_discount([Decimal("0")], Decimal("0")) == [Decimal("0")]


@pytest.mark.asyncio
async def test_issue_draft_moves_stock_writes_vat_and_sets_issued():
    conn = Conn(_invoice(discount="15"))

    out = await issue_invoice(Ctx(conn), INVOICE, {}, BranchChoice(None))

    assert out.status == "issued"
    stock_tx = conn.calls("INSERT INTO tenant_data.stock_transactions")
    # args: tenant, branch, product, type, qty, unit_cost, ref_type, ref_id, notes, reason
    assert [a[1:5] for a in stock_tx] == [(MAIN_BRANCH, P1, "out", Decimal("2")), (MAIN_BRANCH, P2, "out", Decimal("1"))]
    assert all(a[6:8] == ("sale", INVOICE) for a in stock_tx)
    assert conn.stock.locked == [(MAIN_BRANCH, [P1, P2])]
    assert (conn.stock.at(P1), conn.stock.at(P2)) == (Decimal("3"), Decimal("4"))

    vat = conn.calls("INSERT INTO tenant_data.vat_sales_register_lines")
    assert len(vat) == 2
    # args: tenant, invoice_no, date, buyer, description, qty, taxable, vat, discount, total
    assert vat[0][1] == "INV-1" and vat[0][3] == "Rahim"
    assert vat[0][6] == Decimal("200") and vat[0][7] == Decimal("20")
    assert vat[0][8] + vat[1][8] == Decimal("15")
    assert vat[0][9] == Decimal("220") - vat[0][8]
    assert all("'6.3'" in sql for sql, _ in conn.executed if "vat_sales_register_lines" in sql)


@pytest.mark.asyncio
async def test_issue_rejects_short_stock_without_writes():
    conn = Conn(_invoice(), stock={P1: Decimal("1"), P2: Decimal("5")})

    with pytest.raises(HTTPException) as exc:
        await issue_invoice(Ctx(conn), INVOICE, {}, BranchChoice(None))

    assert exc.value.status_code == 409
    assert conn.executed == []


@pytest.mark.asyncio
async def test_issue_rejects_missing_product():
    conn = Conn(_invoice(), stock={P1: Decimal("5")})

    with pytest.raises(HTTPException) as exc:
        await issue_invoice(Ctx(conn), INVOICE, {}, BranchChoice(None))

    assert exc.value.status_code == 400
    assert conn.executed == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["issued", "partially_paid", "paid", "cancelled"])
async def test_issue_rejects_non_draft(status):
    conn = Conn(_invoice(status=status))

    with pytest.raises(HTTPException) as exc:
        await issue_invoice(Ctx(conn), INVOICE, {}, BranchChoice(None))

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_issue_unknown_invoice_404():
    with pytest.raises(HTTPException) as exc:
        await issue_invoice(Ctx(Conn(None)), INVOICE, {}, BranchChoice(None))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_cancel_draft_only_changes_status():
    conn = Conn(_invoice())

    out = await cancel_invoice(Ctx(conn), INVOICE, {})

    assert out.status == "cancelled"
    assert conn.executed == []


@pytest.mark.asyncio
async def test_cancel_issued_restores_stock_and_reverses_vat():
    conn = Conn(_invoice(status="issued", discount="15"))

    out = await cancel_invoice(Ctx(conn), INVOICE, {})

    assert out.status == "cancelled"
    assert conn.locked == [[P1, P2]]
    assert (conn.stock.at(P1), conn.stock.at(P2)) == (Decimal("7"), Decimal("6"))
    restock = conn.calls("INSERT INTO tenant_data.stock_transactions")
    assert [(a[1], a[3], a[5], a[6], a[7]) for a in restock] == [
        (MAIN_BRANCH, "in", Decimal("40"), "sale_cancel", INVOICE)
    ] * 2

    vat = conn.calls("INSERT INTO tenant_data.vat_sales_register_lines")
    assert len(vat) == 2
    assert vat[0][5] == Decimal("-2") and vat[0][6] == Decimal("-200") and vat[0][7] == Decimal("-20")
    assert vat[0][8] + vat[1][8] == Decimal("-15")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invoice, credit_notes",
    [
        (_invoice(status="partially_paid", amount_paid="50"), 0),
        (_invoice(status="paid", amount_paid="330"), 0),
        (_invoice(status="issued"), 1),
        (_invoice(status="cancelled"), 0),
    ],
)
async def test_cancel_rejects_paid_returned_or_cancelled(invoice, credit_notes):
    conn = Conn(invoice, credit_notes=credit_notes)

    with pytest.raises(HTTPException) as exc:
        await cancel_invoice(Ctx(conn), INVOICE, {})

    assert exc.value.status_code == 409
    assert conn.executed == []


@pytest.mark.asyncio
async def test_cancel_rejects_invoice_with_pending_gateway_payment():
    # The customer may still finish paying; a cancel now would restock goods they paid for.
    conn = Conn(_invoice(status="issued"), pending_payments=1)

    with pytest.raises(HTTPException) as exc:
        await cancel_invoice(Ctx(conn), INVOICE, {})

    assert exc.value.status_code == 409
    assert conn.executed == []


class FixedBranch:
    def __init__(self, branch_id):
        self.branch_id = branch_id

    async def resolve(self, conn):
        return self.branch_id


@pytest.mark.asyncio
async def test_issue_takes_stock_from_the_request_branch():
    other = UUID("00000000-0000-0000-0000-0000000000b2")
    conn = Conn(_invoice())
    conn.stock.levels[(other, P1)] = Decimal("5")
    conn.stock.levels[(other, P2)] = Decimal("5")

    await issue_invoice(Ctx(conn), INVOICE, {}, FixedBranch(other))

    stock_tx = conn.calls("INSERT INTO tenant_data.stock_transactions")
    assert {a[1] for a in stock_tx} == {other}
    assert conn.stock.locked == [(other, [P1, P2])]
