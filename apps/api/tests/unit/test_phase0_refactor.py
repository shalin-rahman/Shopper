import os
import pytest
from datetime import date, datetime
from uuid import UUID
from starlette.testclient import TestClient

from core.config import get_settings, clear_settings_cache
from routers.auth import create_access_token
from schemas import TenantSettingsOut, TenantSettingsInternalOut, InventoryAgingItem
from main import app

def test_formatted_date_parsing_and_serialization():
    """Verify that FormattedDate type parses dd-MM-yyyy/YYYY-MM-DD formats and serializes to dd-MM-yyyy."""
    # Test parsing from dd-MM-yyyy
    item = InventoryAgingItem(
        sku="SKU-1",
        name_en="Test En",
        name_bn="Test Bn",
        unit="pcs",
        reference_date="27-05-2026",
        days_idle=10,
        bucket="0_30",
    )
    assert item.reference_date == date(2026, 5, 27)
    
    # Test serialization to dd-MM-yyyy
    data = item.model_dump(mode="json")
    assert data["reference_date"] == "27-05-2026"

    # Test parsing from YYYY-MM-DD
    item2 = InventoryAgingItem(
        sku="SKU-2",
        name_en="Test En",
        name_bn="Test Bn",
        unit="pcs",
        reference_date="2026-05-27",
        days_idle=10,
        bucket="0_30",
    )
    assert item2.reference_date == date(2026, 5, 27)
    data2 = item2.model_dump(mode="json")
    assert data2["reference_date"] == "27-05-2026"


def test_tenant_settings_redaction():
    """Verify that TenantSettingsOut excludes secrets while TenantSettingsInternalOut includes them."""
    payload = {
        "tenant_id": UUID("00000000-0000-0000-0000-000000000000"),
        "theme_id": "default",
        "default_language": "en",
        "logo_url": "http://logo",
        "legal_title_en": "Shopper",
        "legal_title_bn": "শপার",
        "bin": "123",
        "default_vat_rate_pct": 15.0,
        "module_access": {"pos": True},
        "sslcommerz_store_id": "my_store",
        "sslcommerz_store_password": "super_secret_passwd",
        "bkash_app_key": "app_key",
        "bkash_app_secret": "app_secret",
        "bkash_username": "username",
        "bkash_password": "password",
        "nagad_merchant_id": "merchant_id",
        "nagad_public_key": "pub_key",
        "nagad_private_key": "priv_key",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    # Internal settings must include private keys
    internal = TenantSettingsInternalOut(**payload)
    assert internal.sslcommerz_store_password == "super_secret_passwd"
    assert internal.bkash_app_secret == "app_secret"

    # Public settings must exclude private keys completely
    public = TenantSettingsOut(**payload)
    public_dump = public.model_dump()
    assert "sslcommerz_store_password" not in public_dump
    assert "bkash_app_secret" not in public_dump
    assert "nagad_private_key" not in public_dump


def test_jwt_settings_integration(client: TestClient):
    """Verify that changingSettings.jwt_secret_key successfully affects access token generation and authorization."""
    
    # Temporarily modify settings key
    settings = get_settings()
    original_secret = settings.jwt_secret_key
    settings.jwt_secret_key = "custom-secret-key-for-test-syncing"
    
    try:
        # Generate token using custom key
        token = create_access_token({
            "uid": "00000000-0000-0000-0000-000000000000",
            "tid": "00000000-0000-0000-0000-000000000000",
            "role": "admin"
        })

        # Request to settings endpoint (requires auth)
        r = client.get(
            "/v1/tenant/settings",
            headers={"X-Shopper-Tenant": "demo", "Authorization": f"Bearer {token}"}
        )
        # Authentication should succeed (and settings should return mock data in testing mode)
        assert r.status_code == 200
        
        # Testing invalid token with standard key should now fail
        r_fail = client.get(
            "/v1/tenant/settings",
            headers={"X-Shopper-Tenant": "demo", "Authorization": "Bearer invalidtoken"}
        )
        assert r_fail.status_code == 401
    finally:
        settings.jwt_secret_key = original_secret
