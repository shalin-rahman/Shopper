from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from core.config import get_settings
from schemas import PaymentCreate, PaymentGateway, TenantSettingsInternalOut
from services.payment_gateway import SSLCommerzGateway

TENANT = {"X-Shopper-Tenant": "demo"}


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("result", ["success", "fail", "cancel"])
def test_return_redirects_to_web_result_page(client, method, result):
    r = client.request(
        method, f"/v1/storefront/checkout/return/{result}", headers=TENANT, follow_redirects=False
    )
    assert r.status_code == 303
    assert r.headers["location"] == f"/checkout/result?status={result}"


def test_gateway_form_post_is_accepted(client):
    r = client.post(
        "/v1/storefront/checkout/return/success",
        data={"tran_id": "abc", "status": "VALID"},
        headers=TENANT,
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_unknown_result_is_rejected(client):
    r = client.post("/v1/storefront/checkout/return/other", headers=TENANT, follow_redirects=False)
    assert r.status_code == 422


def _tenant_settings() -> TenantSettingsInternalOut:
    now = datetime.now()
    return TenantSettingsInternalOut(
        tenant_id=uuid4(),
        theme_id="emerald",
        default_language="en",
        logo_url=None,
        legal_title_en="Acme",
        legal_title_bn=None,
        bin=None,
        default_vat_rate_pct=Decimal("15"),
        module_access={},
        created_at=now,
        updated_at=now,
        sslcommerz_store_id="testacme",
        sslcommerz_store_password="secret",
    )


@pytest.mark.parametrize(
    "base, host",
    [
        ("https://shop.example", "https://acme.shop.example"),
        ("https://{subdomain}.shop.example/", "https://acme.shop.example"),
    ],
)
async def test_sslcommerz_urls_go_through_tenant_host(monkeypatch, base, host):
    sent: dict = {}

    async def fake_post(self, url, data=None, **kwargs):
        sent.update(data)
        return httpx.Response(
            200,
            json={"status": "SUCCESS", "GatewayPageURL": "https://gw", "sessionkey": "k"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    settings = get_settings().model_copy(
        update={"storefront_public_base_url": base, "platform_root_domain": "shopper.com"}
    )
    payment = PaymentCreate(gateway=PaymentGateway.sslcommerz, amount=Decimal("100.00"))

    out = await SSLCommerzGateway(settings).initiate_payment(payment, "acme", settings, _tenant_settings())

    assert out == {"gateway_url": "https://gw", "sessionkey": "k"}
    assert sent["ipn_url"] == f"{host}/api/v1/tenant/payments/ipn/sslcommerz?tenant=acme"
    assert sent["success_url"] == f"{host}/api/v1/storefront/checkout/return/success"
    assert sent["fail_url"] == f"{host}/api/v1/storefront/checkout/return/fail"
    assert sent["cancel_url"] == f"{host}/api/v1/storefront/checkout/return/cancel"
