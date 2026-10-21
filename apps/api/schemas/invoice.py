from __future__ import annotations
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from schemas.customer import CustomerCreate

class InvoiceLineBase(BaseModel):
    product_id: UUID | None = None
    description: str = Field(..., min_length=1)
    qty: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    vat_rate_pct: Decimal = Field(default=Decimal("0"), ge=0)

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
    invoice_no: str = Field(..., min_length=1, max_length=128)
    lines: list[InvoiceLineCreate] = Field(..., min_length=1)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = None

class InvoiceOut(BaseModel):
    id: UUID
    tenant_id: UUID
    customer_id: UUID | None
    invoice_no: str
    subtotal: Decimal
    discount: Decimal = Decimal("0")
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

class SalesReturnCreate(BaseModel):
    invoice_id: UUID
    reason: str
    items: list["SalesReturnLineCreate"] = Field(..., min_length=1)

class SalesReturnLineCreate(BaseModel):
    product_id: UUID
    qty: Decimal = Field(..., gt=0)

class CreditNoteOut(BaseModel):
    id: UUID
    note_no: str
    invoice_id: UUID
    reason: str | None
    total_adjustment: Decimal
    discount_amount: Decimal = Decimal("0")
    created_at: datetime

    model_config = {"from_attributes": True}
