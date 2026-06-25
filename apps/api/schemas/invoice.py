from __future__ import annotations
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from schemas.customer import CustomerCreate

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
