from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from pydantic import BaseModel

class TenantSettingsOut(BaseModel):
    tenant_id: UUID
    theme_id: str
    default_language: str
    logo_url: str | None
    legal_title_en: str | None
    legal_title_bn: str | None
    bin: str | None
    default_vat_rate_pct: Decimal
    module_access: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class TenantSettingsInternalOut(TenantSettingsOut):
    sslcommerz_store_id: str | None = None
    sslcommerz_store_password: str | None = None
    bkash_app_key: str | None = None
    bkash_app_secret: str | None = None
    bkash_username: str | None = None
    bkash_password: str | None = None
    nagad_merchant_id: str | None = None
    nagad_public_key: str | None = None
    nagad_private_key: str | None = None
