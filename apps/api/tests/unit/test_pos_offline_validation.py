from decimal import Decimal
from contextlib import asynccontextmanager
from copy import deepcopy
from uuid import UUID

import pytest

from routers.pos import parse_offline_punch_orders, pos_offline_punch


def test_parse_offline_punch_orders_accepts_valid_payload():
    payload = [{
        "id": "8d5b1ffa-6f2b-49b7-ae6d-fe6d16d2fe6a",
        "orderNumber": "POS-100",
        "total": "172.50",
        "subtotal": "150.00",
        "taxAmount": "22.50",
        "customerName": "Jane Doe",
        "customerPhone": "01700000001",
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "150.00",
            "vatRatePct": "15.0",
            "vatAmount": "22.50",
        }],
    }]

    orders, rejected = parse_offline_punch_orders(payload)

    assert len(orders) == 1
    assert rejected == []
    assert orders[0].order_number == "POS-100"
    assert orders[0].payment_method == "cash"
    assert orders[0].items[0].line_total == Decimal("172.50")


def test_parse_offline_punch_orders_accepts_explicit_payment_method():
    payload = [{
        "id": "POS-LOCAL-PAYMENT",
        "orderNumber": "POS-101",
        "total": "10.00",
        "subtotal": "10.00",
        "paymentMethod": "bkash",
        "amountPaid": "4.00",
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "10.00",
        }],
    }]

    orders, rejected = parse_offline_punch_orders(payload)

    assert rejected == []
    assert orders[0].payment_method == "bkash"
    assert orders[0].collected_amount == Decimal("4.00")


def test_parse_offline_punch_orders_defaults_omitted_collection_to_unpaid():
    payload = [{
        "id": "POS-LOCAL-UNPAID",
        "orderNumber": "POS-103",
        "total": "10.00",
        "subtotal": "10.00",
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "10.00",
        }],
    }]

    orders, rejected = parse_offline_punch_orders(payload)

    assert rejected == []
    assert orders[0].amount_paid is None
    assert orders[0].collected_amount == Decimal("0")


@pytest.mark.parametrize(
    ("payment_method", "amount_paid"),
    [("cash", "10.01"), ("credit", "0.01")],
)
def test_parse_offline_punch_orders_rejects_overpayment_and_paid_credit(
    payment_method, amount_paid
):
    payload = [{
        "id": "POS-LOCAL-INVALID-COLLECTION",
        "orderNumber": "POS-104",
        "total": "10.00",
        "subtotal": "10.00",
        "amount_paid": amount_paid,
        "payment_method": payment_method,
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "10.00",
        }],
    }]

    orders, rejected = parse_offline_punch_orders(payload)

    assert orders == []
    assert rejected


def test_parse_offline_punch_orders_rejects_unknown_payment_method():
    payload = [{
        "id": "POS-LOCAL-UNKNOWN-METHOD",
        "orderNumber": "POS-102",
        "total": "10.00",
        "subtotal": "10.00",
        "payment_method": "crypto",
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "10.00",
        }],
    }]

    orders, rejected = parse_offline_punch_orders(payload)

    assert orders == []
    assert "payment_method" in str(rejected[0]["error"])


def test_parse_offline_punch_orders_rejects_invalid_orders():
    payload = [
        {
            "id": "14e095ac-c82a-4b26-94d2-eb9c1f9eeef2",
            "orderNumber": "POS-200",
            "total": "40.00",
            "subtotal": "35.00",
            "taxAmount": "5.00",
            "items": [{
                "productId": "22222222-2222-4222-8222-222222222222",
                "productName": "Broken Item",
                "quantity": 0,
                "unitPrice": "10.00",
                "vatRatePct": "0",
                "vatAmount": "0",
            }],
        },
        {
            "id": "3b50f3b8-5d27-4988-80be-4df6c2008873",
            "orderNumber": "POS-201",
            "total": "120.00",
            "subtotal": "120.00",
            "taxAmount": "0",
            "items": [],
        },
    ]

    orders, rejected = parse_offline_punch_orders(payload)

    assert orders == []
    assert len(rejected) == 2
    assert rejected[0]["local_id"] == payload[0]["id"]
    assert any("quantity" in str(error) for error in str(rejected[0]["error"]).split())


def test_parse_offline_punch_orders_rejects_mismatched_vat():
    payload = [{
        "id": "POS-LOCAL-3",
        "orderNumber": "POS-300",
        "total": "165.00",
        "subtotal": "150.00",
        "taxAmount": "15.00",
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "150.00",
            "vatRatePct": "15",
            "vatAmount": "5.00",
        }],
    }]

    orders, rejected = parse_offline_punch_orders(payload)

    assert orders == []
    assert "VAT amount" in str(rejected[0]["error"])


class _FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        self.snapshot = deepcopy(self.connection.state)
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if exc_type:
            self.connection.state = self.snapshot
        return False


class _FakeConnection:
    def __init__(self):
        self.state = {
            "invoices": {},
            "effects": [],
            "active": True,
            "stock_quantity": Decimal("10"),
            "fail_on_vat_insert": False,
        }

    def transaction(self):
        return _FakeTransaction(self)

    async def fetchrow(self, query, *args):
        if "source_order_id = $2" in query:
            return self.state["invoices"].get(args[1])
        if "invoice_no = $2" in query:
            return next(
                (row for row in self.state["invoices"].values() if row["invoice_no"] == args[1]),
                None,
            )
        raise AssertionError(f"Unexpected fetchrow query: {query}")

    async def fetch(self, query, *args):
        if "FROM tenant_data.products" in query:
            return [{
                "id": product_id,
                "is_active": self.state["active"],
                "stock_quantity": self.state["stock_quantity"],
            } for product_id in args[0]]
        raise AssertionError(f"Unexpected fetch query: {query}")

    async def fetchval(self, query, *args):
        if "INSERT INTO tenant_data.invoices" in query:
            invoice_id = UUID("00000000-0000-0000-0000-000000000099")
            self.state["invoices"][args[2]] = {
                "id": invoice_id,
                "invoice_no": args[1],
                "status": "issued",
                "amount_paid": Decimal("0"),
                "balance_due": args[3],
                "pos_tender": args[10],
            }
            self.state["effects"].append(("invoice", args[1]))
            return invoice_id
        raise AssertionError(f"Unexpected fetchval query: {query}")

    async def execute(self, query, *args):
        if self.state["fail_on_vat_insert"] and "vat_sales_register_lines" in query:
            raise RuntimeError("simulated register failure")
        if "stock_quantity = stock_quantity -" in query:
            self.state["stock_quantity"] -= Decimal(str(args[0]))
        effect = "settlement" if "invoice_settlements" in query else query.strip().split()[0]
        self.state["effects"].append((effect, args))


class _FakeTenantContext:
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")

    def __init__(self, connection):
        self.connection = connection

    @asynccontextmanager
    async def transaction(self):
        async with self.connection.transaction():
            yield self.connection


@pytest.mark.asyncio
async def test_offline_sync_is_replay_safe_and_reduces_stock_once():
    connection = _FakeConnection()
    context = _FakeTenantContext(connection)
    payload = [{
        "id": "POS-LOCAL-1",
        "orderNumber": "POS-101",
        "total": "172.50",
        "subtotal": "150.00",
        "taxAmount": "22.50",
        "amountPaid": "100.00",
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "150.00",
            "vatRatePct": "15",
            "vatAmount": "22.50",
        }],
    }]

    first_result = await pos_offline_punch(context, payload, None)
    second_result = await pos_offline_punch(context, payload, None)

    assert first_result["status"] == "success"
    assert second_result["status"] == "success"
    assert len(connection.state["invoices"]) == 1
    assert len([effect for effect in connection.state["effects"] if effect[0] == "UPDATE"]) == 1
    assert len([effect for effect in connection.state["effects"] if effect[0] == "settlement"]) == 1
    settlement = next(effect for effect in connection.state["effects"] if effect[0] == "settlement")
    assert settlement[1][2] == Decimal("100.00")
    assert connection.state["stock_quantity"] == Decimal("9")


@pytest.mark.asyncio
async def test_offline_sync_keeps_omitted_collection_unpaid_without_settlement():
    connection = _FakeConnection()
    context = _FakeTenantContext(connection)
    payload = [{
        "id": "POS-LOCAL-UNPAID",
        "orderNumber": "POS-105",
        "total": "10.00",
        "subtotal": "10.00",
        "payment_method": "credit",
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "10.00",
        }],
    }]

    result = await pos_offline_punch(context, payload, None)

    assert result["status"] == "success"
    invoice = connection.state["invoices"]["POS-LOCAL-UNPAID"]
    assert invoice["status"] == "issued"
    assert invoice["amount_paid"] == Decimal("0")
    assert invoice["balance_due"] == Decimal("10.00")
    assert invoice["pos_tender"] == "credit"
    assert not any(effect[0] == "settlement" for effect in connection.state["effects"])


@pytest.mark.asyncio
async def test_offline_sync_rejects_insufficient_aggregate_stock():
    connection = _FakeConnection()
    connection.state["stock_quantity"] = Decimal("10")
    context = _FakeTenantContext(connection)
    product_id = "11111111-1111-4111-8111-111111111111"
    payload = [{
        "id": "POS-LOCAL-OVERSOLD",
        "orderNumber": "POS-106",
        "total": "120.00",
        "subtotal": "120.00",
        "items": [
            {
                "productId": product_id,
                "productName": "Widget",
                "quantity": 6,
                "unitPrice": "10.00",
            },
            {
                "productId": product_id,
                "productName": "Widget",
                "quantity": 6,
                "unitPrice": "10.00",
            },
        ],
    }]

    result = await pos_offline_punch(context, payload, None)

    assert result["status"] == "failed"
    assert result["synced_count"] == 0
    assert "Insufficient stock" in str(result["rejected"][0]["error"])
    assert connection.state["invoices"] == {}
    assert connection.state["stock_quantity"] == Decimal("10")


@pytest.mark.asyncio
async def test_offline_sync_rolls_back_a_failed_order():
    connection = _FakeConnection()
    connection.state["fail_on_vat_insert"] = True
    context = _FakeTenantContext(connection)
    payload = [{
        "id": "POS-LOCAL-2",
        "orderNumber": "POS-102",
        "total": "172.50",
        "subtotal": "150.00",
        "taxAmount": "22.50",
        "items": [{
            "productId": "11111111-1111-4111-8111-111111111111",
            "productName": "Widget",
            "quantity": 1,
            "unitPrice": "150.00",
            "vatRatePct": "15",
            "vatAmount": "22.50",
        }],
    }]

    result = await pos_offline_punch(context, payload, None)

    assert result["status"] == "failed"
    assert result["synced_count"] == 0
    assert result["rejected"][0]["local_id"] == "POS-LOCAL-2"
    assert connection.state["invoices"] == {}
    assert connection.state["effects"] == []
