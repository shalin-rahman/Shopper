from __future__ import annotations
from decimal import Decimal
from enum import Enum
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class PaymentGateway(str, Enum):
    sslcommerz = "sslcommerz"
    bkash = "bkash"
    nagad = "nagad"
    rocket = "rocket"

class PaymentCreate(BaseModel):
    gateway: PaymentGateway
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=2)
    currency: str = "BDT"
    description: str | None = None
    order_id: str | None = None
    invoice_id: UUID | None = None

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
