from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field

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

class TenantSettingsUpdate(BaseModel):
    theme_id: str | None = Field(default=None, min_length=1, max_length=64)
    default_language: Literal["en", "bn"] | None = None
    logo_url: str | None = Field(default=None, max_length=2048)
    legal_title_en: str | None = None
    legal_title_bn: str | None = None
    bin: str | None = Field(default=None, max_length=64)
    default_vat_rate_pct: Decimal | None = Field(default=None, ge=0, le=100)
    module_access: dict[str, bool] | None = None

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
