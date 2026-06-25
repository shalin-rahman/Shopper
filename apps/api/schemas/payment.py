from __future__ import annotations
from decimal import Decimal
from enum import Enum
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

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
