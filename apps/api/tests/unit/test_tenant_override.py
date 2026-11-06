from types import SimpleNamespace

from core.config import Settings
from core.host_tenant import subdomain_from_host
from core.tenant_context import subdomain_from_request


def _request(settings, header=None, host_sub=None):
    headers = {"X-Shopper-Tenant": header} if header else {}
    return SimpleNamespace(
        headers=headers,
        state=SimpleNamespace(tenant_subdomain=host_sub),
        app=SimpleNamespace(state=SimpleNamespace(settings=settings)),
    )


def test_override_defaults_off(monkeypatch):
    monkeypatch.delenv("ALLOW_TENANT_OVERRIDE", raising=False)
    assert Settings(_env_file=None).allow_tenant_override is False


def test_dev_hosts_ignored_without_override():
    assert subdomain_from_host("localhost:8000") is None
    assert subdomain_from_host("127.0.0.1") is None
    assert subdomain_from_host("acme.localhost") is None


def test_dev_hosts_map_with_override():
    assert subdomain_from_host("localhost:8000", allow_dev_hosts=True) == "demo"
    assert subdomain_from_host("acme.localhost", allow_dev_hosts=True) == "acme"


def test_root_domain_works_either_way():
    assert subdomain_from_host("t1.platform.test", platform_root_domain="platform.test") == "t1"


def test_header_ignored_without_override():
    settings = Settings(_env_file=None, allow_tenant_override=False)
    assert subdomain_from_request(_request(settings, header="victim", host_sub="acme")) == "acme"


def test_header_used_with_override():
    settings = Settings(_env_file=None, allow_tenant_override=True)
    assert subdomain_from_request(_request(settings, header="Demo ", host_sub="acme")) == "demo"
