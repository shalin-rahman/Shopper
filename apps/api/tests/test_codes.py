from codes import barcode_for_sku, qr_payload_for_product


def test_barcode_for_sku_alphanumeric():
    assert barcode_for_sku("SKU-99") == "SKU99"


def test_barcode_for_sku_short_generates_numeric():
    b = barcode_for_sku("a")
    assert b.startswith("SK")
    assert len(b) == 14


def test_qr_payload():
    url = qr_payload_for_product("https://shop.example", "acme", "SKU-1")
    assert url == "https://shop.example/acme/p/SKU-1"


def test_qr_payload_empty_base_uses_placeholder():
    url = qr_payload_for_product("", "t", "x")
    assert "publicportal.example" in url
    assert url.endswith("/t/p/x")
