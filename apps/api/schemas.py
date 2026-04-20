from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
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
    stock_quantity: Decimal = Field(default=Decimal("0"))


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
    stock_quantity: Decimal | None = None


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
    sslcommerz_store_id: str | None = None
    sslcommerz_store_password: str | None = None
    bkash_app_key: str | None = None
    bkash_app_secret: str | None = None
    bkash_username: str | None = None
    bkash_password: str | None = None
    nagad_merchant_id: str | None = None
    nagad_public_key: str | None = None
    nagad_private_key: str | None = None
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
    stock_quantity: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name_en: str = Field(..., min_length=1)
    name_bn: str = Field(..., min_length=1)
    phone: str | None = None
    email: str | None = None
    billing_address_en: str | None = None
    billing_address_bn: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name_en: str | None = None
    name_bn: str | None = None
    phone: str | None = None
    email: str | None = None
    billing_address_en: str | None = None
    billing_address_bn: str | None = None


class CustomerOut(BaseModel):
    id: UUID
    tenant_id: UUID
    code: str
    name_en: str
    name_bn: str
    phone: str | None
    email: str | None
    billing_address_en: str | None
    billing_address_bn: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentGateway(str, Enum):
    sslcommerz = "sslcommerz"
    bkash = "bkash"
    nagad = "nagad"
    rocket = "rocket"


class PaymentCreate(BaseModel):
    gateway: PaymentGateway
    amount: Decimal
    currency: str = "BDT"
    description: str | None = None
    order_id: str | None = None


class PaymentOut(BaseModel):
    id: UUID
    gateway: PaymentGateway
    amount: Decimal
    currency: str
    status: str
    gateway_transaction_id: str | None
    gateway_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceLineBase(BaseModel):
    product_id: UUID | None = None
    description: str
    qty: Decimal
    unit_price: Decimal
    vat_rate_pct: Decimal = Field(default=Decimal("0"))


class InvoiceLineCreate(InvoiceLineBase):
    pass


class InvoiceLineOut(InvoiceLineBase):
    id: UUID
    vat_amount: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    customer_id: UUID | None = None
    invoice_no: str
    lines: list[InvoiceLineCreate]
    notes: str | None = None


class InvoiceOut(BaseModel):
    id: UUID
    tenant_id: UUID
    customer_id: UUID | None
    invoice_no: str
    subtotal: Decimal
    total_vat: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    lines: list[InvoiceLineOut] = []

    model_config = {"from_attributes": True}


class StorefrontProductOut(BaseModel):
    id: UUID
    sku: str
    name_en: str
    name_bn: str
    description_en: str | None = None
    description_bn: str | None = None
    unit: str
    sell_price: Decimal | None = None
    mrp: Decimal | None = None
    vat_rate_pct: Decimal
    barcode: str | None = None
    qr_payload: str | None = None


class StorefrontProductListResponse(BaseModel):
    tenant: str
    products: list[StorefrontProductOut]
    total: int


# --- Reports ---

InventoryAgingBucket = Literal["0_30", "31_60", "61_90", "90_plus"]

class InventoryAgingItem(BaseModel):
    sku: str
    name_en: str
    name_bn: str
    unit: str
    sell_price: Decimal | None = None
    reference_date: date
    days_idle: int
    bucket: InventoryAgingBucket

class InventoryAgingReportOut(BaseModel):
    as_of: date
    items: list[InventoryAgingItem]
    summary: dict[str, int]

class StockValuationItem(BaseModel):
    sku: str
    name_en: str
    name_bn: str
    stock_quantity: Decimal
    wac_cost: Decimal
    total_value: Decimal

class StockValuationReportOut(BaseModel):
    total_inventory_value: Decimal
    items: list[StockValuationItem]

class VatRegisterLineOut(BaseModel):
    invoice_no: str
    invoice_date: date
    buyer_name_en: str | None
    qty: Decimal
    taxable_value: Decimal
    vat_amount: Decimal
    total_amount: Decimal

class VatRegisterReportOut(BaseModel):
    start_date: date
    end_date: date
    total_taxable_value: Decimal
    total_vat_amount: Decimal
    lines: list[VatRegisterLineOut]
