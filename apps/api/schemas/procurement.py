from __future__ import annotations
from decimal import Decimal
from typing import Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

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
