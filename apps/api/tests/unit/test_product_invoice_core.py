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

    discount = _apply_return_discount(allocations, Decimal("20"), Decimal("220"))

    assert allocations[0]["unit_price"] == Decimal("100")
    assert allocations[0]["qty"] == Decimal("1")
    assert discount == Decimal("10")
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
