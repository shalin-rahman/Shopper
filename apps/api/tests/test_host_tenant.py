from host_tenant import subdomain_from_host


def test_localhost_demo_fallback():
    assert subdomain_from_host("localhost:8000") == "demo"
    assert subdomain_from_host("127.0.0.1") == "demo"


def test_subdomain_localhost():
    assert subdomain_from_host("acme.localhost") == "acme"


def test_platform_root_domain():
    assert subdomain_from_host("t1.platform.test", platform_root_domain="platform.test") == "t1"
    assert subdomain_from_host("platform.test", platform_root_domain="platform.test") is None


def test_unknown_host():
    assert subdomain_from_host("evil.com") is None
