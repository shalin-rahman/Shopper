from core.storefront_url import tenant_storefront_url


def test_unset_base_uses_shopper_domain():
    assert tenant_storefront_url(None, "acme") == "https://acme.shopper.com"
    assert tenant_storefront_url("", "acme") == "https://acme.shopper.com"


def test_plain_base_gets_subdomain():
    assert tenant_storefront_url("https://publicportal.example", "acme") == "https://acme.publicportal.example"


def test_trailing_slash_is_dropped():
    assert tenant_storefront_url("https://publicportal.example/", "acme") == "https://acme.publicportal.example"


def test_placeholder_is_replaced_not_prefixed():
    url = tenant_storefront_url("https://{subdomain}.shop.example", "acme")
    assert url == "https://acme.shop.example"
    assert tenant_storefront_url("https://shop.example/{subdomain}/", "acme") == "https://shop.example/acme"


def test_port_and_path_are_kept():
    assert tenant_storefront_url("http://shop.example:8080/store/", "acme") == "http://acme.shop.example:8080/store"


def test_base_without_scheme_defaults_to_https():
    assert tenant_storefront_url("shop.example", "acme") == "https://acme.shop.example"
