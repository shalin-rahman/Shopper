from __future__ import annotations
from decimal import Decimal
from typing import Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

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
