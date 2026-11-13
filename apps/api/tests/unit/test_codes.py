from utils.codes import barcode_for_sku, qr_payload_for_product


def test_barcode_for_sku_alphanumeric():
    assert barcode_for_sku("SKU-99") == "SKU99"


def test_barcode_for_sku_short_generates_numeric():
    b = barcode_for_sku("a")
    assert b.startswith("SK")
    assert len(b) == 14


def test_qr_payload_puts_tenant_in_host():
    url = qr_payload_for_product("https://shop.example/", "acme", "SKU-1")
    assert url == "https://acme.shop.example/p/SKU-1"


def test_qr_payload_fills_placeholder():
    url = qr_payload_for_product("https://{subdomain}.shop.example", "acme", "SKU-1")
    assert url == "https://acme.shop.example/p/SKU-1"


def test_qr_payload_empty_base_uses_default_host():
    assert qr_payload_for_product("", "t", "x") == "https://t.shopper.com/p/x"


def test_qr_payload_escapes_sku():
    assert qr_payload_for_product("https://shop.example", "acme", "A B/1") == "https://acme.shop.example/p/A%20B%2F1"
