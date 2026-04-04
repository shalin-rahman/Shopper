from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=128)
    name_en: str = Field(..., min_length=1)
    name_bn: str = Field(..., min_length=1)
    description_en: str | None = None
    description_bn: str | None = None
    unit: str = Field(default="pcs", max_length=32)
    buy_price: Decimal | None = None
    sell_price: Decimal | None = None
    mrp: Decimal | None = None
    vat_rate_pct: Decimal = Field(default=Decimal("0"))
    category_id: UUID | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name_en: str | None = None
    name_bn: str | None = None
    description_en: str | None = None
    description_bn: str | None = None
    unit: str | None = None
    buy_price: Decimal | None = None
    sell_price: Decimal | None = None
    mrp: Decimal | None = None
    vat_rate_pct: Decimal | None = None
    category_id: UUID | None = None
    is_active: bool | None = None


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


class ProductOut(BaseModel):
    id: UUID
    tenant_id: UUID
    category_id: UUID | None
    sku: str
    name_en: str
    name_bn: str
    description_en: str | None
    description_bn: str | None
    unit: str
    buy_price: Decimal | None
    sell_price: Decimal | None
    mrp: Decimal | None
    vat_rate_pct: Decimal
    barcode: str | None
    qr_payload: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
