from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from routers.invoices import (
    _allocate_return_item,
    _apply_return_discount,
    _calculate_invoice_totals,
)
from routers.products import _row_to_out
from schemas import (
    InvoiceCreate,
    InvoiceLineCreate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    SalesReturnLineCreate,
)


def test_calculate_invoice_totals_respects_vat():
    lines = [
        InvoiceLineCreate(
            product_id=UUID("00000000-0000-0000-0000-000000000001"),
            description="Widget",
            qty=Decimal("2"),
            unit_price=Decimal("100"),
            vat_rate_pct=Decimal("10"),
        )
    ]

    subtotal, vat, total_amount, processed = _calculate_invoice_totals(lines)

    assert subtotal == Decimal("200")
    assert vat == Decimal("20")
    assert total_amount == Decimal("220")
    assert processed[0]["line_total"] == Decimal("220")

def test_calculate_invoice_totals_applies_discount_after_vat():
    line = InvoiceLineCreate(
        description="Widget",
        qty=Decimal("2"),
        unit_price=Decimal("100"),
        vat_rate_pct=Decimal("10"),
    )

    subtotal, vat, total_amount, _ = _calculate_invoice_totals([line], Decimal("15"))

    assert subtotal == Decimal("200")
    assert vat == Decimal("20")
    assert total_amount == Decimal("205")

def test_product_schemas_reject_negative_prices_and_stock():
    with pytest.raises(ValidationError):
        ProductCreate(
            sku="SKU-1",
            name_en="Widget",
            name_bn="পণ্য",
            sell_price=Decimal("-1"),
        )

    with pytest.raises(ValidationError):
        ProductUpdate(stock_quantity=Decimal("-1"))

    with pytest.raises(ValidationError):
        ProductUpdate(stock_quantity=None)

def test_invoice_schema_requires_lines_and_nonnegative_discount():
    with pytest.raises(ValidationError):
        InvoiceCreate(invoice_no="INV-1", lines=[])

    with pytest.raises(ValidationError):
        InvoiceCreate(
            invoice_no="INV-1",
            discount=Decimal("-1"),
            lines=[{"description": "Widget", "qty": 1, "unit_price": 10}],
        )

def test_sales_return_uses_original_invoice_price_and_allocates_discount():
    invoice_line_id = UUID("00000000-0000-0000-0000-000000000040")
    product_id = UUID("00000000-0000-0000-0000-000000000050")
    returned_by_line = {}
    allocations = _allocate_return_item(
        SalesReturnLineCreate(product_id=product_id, qty=Decimal("1")),
        [{
            "id": invoice_line_id,
            "product_id": product_id,
            "qty": Decimal("2"),
            "unit_price": Decimal("100"),
            "vat_rate_pct": Decimal("10"),
        }],
        returned_by_line,
    )

    terms = {invoice_line_id: {"qty": Decimal("2"), "share": Decimal("20"),
                               "returned_qty": Decimal("0"), "returned_discount": Decimal("0")}}
    discount = _apply_return_discount(allocations, terms)

    assert allocations[0]["unit_price"] == Decimal("100")
    assert allocations[0]["qty"] == Decimal("1")
    assert discount == Decimal("10")
    assert allocations[0]["total_amount"] == Decimal("100")


def _alloc(line_id, qty):
    return {"invoice_line_id": line_id, "qty": Decimal(qty), "total_amount": Decimal("100")}


def test_return_discount_rounds_like_issue_and_last_unit_takes_the_rest():
    line = UUID(int=1)
    terms = {line: {"qty": Decimal("3"), "share": Decimal("10"),
                    "returned_qty": Decimal("0"), "returned_discount": Decimal("0")}}

    first = _apply_return_discount([_alloc(line, "1")], terms)
    assert first == Decimal("3.3333")

    terms[line].update(returned_qty=Decimal("1"), returned_discount=first)
    rest = _apply_return_discount([_alloc(line, "2")], terms)
    # Both returns together give back exactly the share the 6.3 line carried.
    assert rest == Decimal("6.6667")
    assert first + rest == Decimal("10")


def test_return_discount_uses_each_line_share_not_gross():
    # Issue gave line A 6.6667 and line B 3.3333 of a 10 discount.
    a, b = UUID(int=1), UUID(int=2)
    terms = {
        a: {"qty": Decimal("1"), "share": Decimal("6.6667"),
            "returned_qty": Decimal("0"), "returned_discount": Decimal("0")},
        b: {"qty": Decimal("1"), "share": Decimal("3.3333"),
            "returned_qty": Decimal("0"), "returned_discount": Decimal("0")},
    }
    allocations = [_alloc(b, "1")]

    assert _apply_return_discount(allocations, terms) == Decimal("3.3333")
    assert allocations[0]["discount_amount"] == Decimal("3.3333")
    assert allocations[0]["total_amount"] == Decimal("96.6667")


def test_return_discount_same_line_twice_in_one_note():
    line = UUID(int=1)
    terms = {line: {"qty": Decimal("3"), "share": Decimal("10"),
                    "returned_qty": Decimal("0"), "returned_discount": Decimal("0")}}
    allocations = [_alloc(line, "1"), _alloc(line, "2")]

    assert _apply_return_discount(allocations, terms) == Decimal("10")
    assert [a["discount_amount"] for a in allocations] == [Decimal("3.3333"), Decimal("6.6667")]

def test_return_discount_never_negative_after_an_old_style_note():
    # A note from before the per-line split gave back more than this line's share.
    line = UUID(int=1)
    terms = {line: {"qty": Decimal("2"), "share": Decimal("5"),
                    "returned_qty": Decimal("1"), "returned_discount": Decimal("7")}}
    allocations = [_alloc(line, "1")]

    assert _apply_return_discount(allocations, terms) == Decimal("0")
    assert allocations[0]["total_amount"] == Decimal("100")

def test_sales_return_rejects_quantity_beyond_remaining_sold_units():
    invoice_line_id = UUID("00000000-0000-0000-0000-000000000060")
    product_id = UUID("00000000-0000-0000-0000-000000000070")

    with pytest.raises(HTTPException) as exc:
        _allocate_return_item(
            SalesReturnLineCreate(product_id=product_id, qty=Decimal("2")),
            [{
                "id": invoice_line_id,
                "product_id": product_id,
                "qty": Decimal("2"),
                "unit_price": Decimal("100"),
                "vat_rate_pct": Decimal("0"),
            }],
            {invoice_line_id: Decimal("1")},
        )

    assert exc.value.status_code == 400


def test_row_to_out_converts_decimal_fields_for_products():
    row = {
        "id": UUID("00000000-0000-0000-0000-000000000010"),
        "tenant_id": UUID("00000000-0000-0000-0000-000000000020"),
        "category_id": UUID("00000000-0000-0000-0000-000000000030"),
        "sku": "SKU-1",
        "name_en": "Phone",
        "name_bn": "ফোন",
        "description_en": "Smartphone",
        "description_bn": "স্মার্টফোন",
        "unit": "pcs",
        "buy_price": "500",
        "sell_price": "650",
        "mrp": "700",
        "vat_rate_pct": "5",
        "barcode": "BC-123",
        "qr_payload": "QR-123",
        "stock_quantity": "15",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    out = _row_to_out(row)

    assert isinstance(out, ProductOut)
    assert out.stock_quantity == Decimal("15")
    assert out.sell_price == Decimal("650")
    assert out.vat_rate_pct == Decimal("5")
