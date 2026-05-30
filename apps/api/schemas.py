from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Annotated
from uuid import UUID

from pydantic import BaseModel, Field, BeforeValidator, PlainSerializer

def parse_date(v: Any) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(v.strip(), fmt).date()
            except ValueError:
                pass
    raise ValueError("Invalid date format, expected dd-MM-yyyy or YYYY-MM-DD")

FormattedDate = Annotated[
    date,
    BeforeValidator(parse_date),
    PlainSerializer(lambda v: v.strftime("%d-%m-%Y"), return_type=str),
]


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


class CustomerCollectionCreate(BaseModel):
    customer_id: UUID
    amount: Decimal
    payment_method: Literal["cash", "bkash", "nagad", "bank"]
    reference_no: str | None = None
    notes: str | None = None


class CustomerCollectionOut(BaseModel):
    id: UUID
    customer_id: UUID
    amount: Decimal
    payment_method: str
    reference_no: str | None
    notes: str | None
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
    customer_data: CustomerCreate | None = None # Smart inline saving
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
    reference_date: FormattedDate
    days_idle: int
    bucket: InventoryAgingBucket

class InventoryAgingReportOut(BaseModel):
    as_of: FormattedDate
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
    invoice_date: FormattedDate
    buyer_name_en: str | None
    qty: Decimal
    taxable_value: Decimal
    vat_amount: Decimal
    total_amount: Decimal

class VatRegisterReportOut(BaseModel):
    start_date: FormattedDate
    end_date: FormattedDate
    total_taxable_value: Decimal
    total_vat_amount: Decimal
    lines: list[VatRegisterLineOut]

class BusinessAnalyticsOut(BaseModel):
    inventory_turnover_ratio: Decimal
    average_inventory_value: Decimal
    cogs_annualized: Decimal
    eoq_recommendations: list[dict] # List of {sku: str, eoq: float}


class SalesReturnCreate(BaseModel):
    invoice_id: UUID
    reason: str
    items: list[dict] # {product_id: UUID, qty: Decimal}


class CreditNoteOut(BaseModel):
    id: UUID
    note_no: str
    invoice_id: UUID
    reason: str | None
    total_adjustment: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryTransferCreate(BaseModel):
    transfer_no: str
    from_location: str
    to_location: str
    items: list[dict] # {product_id: UUID, qty: Decimal, value: Decimal}


class InventoryTransferOut(BaseModel):
    id: UUID
    transfer_no: str
    from_location: str
    to_location: str
    total_value_taxable: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class DebitNoteOut(BaseModel):
    id: UUID
    note_no: str
    reference_id: UUID | None
    reason: str | None
    total_adjustment: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class PurchaseReturnCreate(BaseModel):
    po_id: UUID
    reason: str
    items: list[dict] # {product_id: UUID, qty: Decimal}


class SupplierBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name_en: str = Field(..., min_length=1)
    name_bn: str = Field(..., min_length=1)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierOut(SupplierBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class POLineBase(BaseModel):
    product_id: UUID
    qty: Decimal
    unit_cost: Decimal


class POLineCreate(POLineBase):
    pass


class POLineOut(POLineBase):
    id: UUID
    line_total: Decimal

    model_config = {"from_attributes": True}


class POCreate(BaseModel):
    supplier_id: UUID
    po_no: str
    lines: list[POLineCreate]


class POOut(BaseModel):
    id: UUID
    tenant_id: UUID
    supplier_id: UUID
    po_no: str
    status: str
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    created_at: datetime
    updated_at: datetime
    lines: list[POLineOut] = []

    model_config = {"from_attributes": True}


class SupplierPaymentCreate(BaseModel):
    supplier_id: UUID
    po_id: UUID | None = None
    payment_no: str
    amount: Decimal
    payment_method: Literal["cash", "bank", "check"]
    ref_no: str | None = None


class SupplierPaymentOut(BaseModel):
    id: UUID
    tenant_id: UUID
    supplier_id: UUID
    po_id: UUID | None
    payment_no: str
    amount: Decimal
    payment_method: str
    ref_no: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
