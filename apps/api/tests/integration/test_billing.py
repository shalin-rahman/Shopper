import pytest
from decimal import Decimal

# Since the calculation logic is currently inline in routers, 
# we'll test the logic concepts or extract a helper.
# For min unit tests, we check expected behavior of the schemas and common math.

def calculate_line_total(qty: Decimal, unit_price: Decimal, vat_rate_pct: Decimal):
    subtotal = qty * unit_price
    vat_amount = (subtotal * vat_rate_pct) / Decimal("100")
    return subtotal, vat_amount, subtotal + vat_amount

def test_vat_calculation():
    qty = Decimal("2")
    price = Decimal("100.00")
    vat = Decimal("15.0")
    
    sub, v_amt, total = calculate_line_total(qty, price, vat)
    
    assert sub == Decimal("200.00")
    assert v_amt == Decimal("30.00")
    assert total == Decimal("230.00")

def test_zero_vat():
    qty = Decimal("5")
    price = Decimal("10.00")
    vat = Decimal("0.0")
    
    sub, v_amt, total = calculate_line_total(qty, price, vat)
    
    assert v_amt == Decimal("0")
    assert total == Decimal("50.00")

def test_rounding_precision():
    # 1/3 qty with vat
    qty = Decimal("0.3333")
    price = Decimal("100.00")
    vat = Decimal("15.0")
    
    sub, v_amt, total = calculate_line_total(qty, price, vat)
    # 33.33 + 15% (4.9995) = 38.3295
    assert sub == Decimal("33.3300")
    assert v_amt == Decimal("4.999500")
