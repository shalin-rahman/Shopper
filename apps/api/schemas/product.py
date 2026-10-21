from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=128)
    name_en: str = Field(..., min_length=1)
    name_bn: str = Field(..., min_length=1)
    description_en: str | None = None
    description_bn: str | None = None
    unit: str = Field(default="pcs", max_length=32)
    buy_price: Decimal | None = Field(default=None, ge=0)
    sell_price: Decimal | None = Field(default=None, ge=0)
    mrp: Decimal | None = Field(default=None, ge=0)
    vat_rate_pct: Decimal = Field(default=Decimal("0"), ge=0)
    category_id: UUID | None = None
    stock_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    marketplace_enabled: bool = False

    @field_validator("sku", "name_en", "name_bn", "unit")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name_en: str | None = None
    name_bn: str | None = None
    description_en: str | None = None
    description_bn: str | None = None
    unit: str | None = None
    buy_price: Decimal | None = Field(default=None, ge=0)
    sell_price: Decimal | None = Field(default=None, ge=0)
    mrp: Decimal | None = Field(default=None, ge=0)
    vat_rate_pct: Decimal | None = Field(default=None, ge=0)
    category_id: UUID | None = None
    is_active: bool | None = None
    stock_quantity: Decimal | None = Field(default=None, ge=0)
    marketplace_enabled: bool | None = None

    @field_validator("name_en", "name_bn", "unit")
    @classmethod
    def validate_required_text_updates(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Field cannot be null")
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value

    @field_validator("stock_quantity")
    @classmethod
    def stock_quantity_must_not_be_null(cls, value: Decimal | None) -> Decimal:
        if value is None:
            raise ValueError("Stock quantity cannot be null")
        return value

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
    stock_quantity: Decimal
    is_active: bool
    marketplace_enabled: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
