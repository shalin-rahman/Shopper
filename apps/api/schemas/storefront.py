from __future__ import annotations
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel

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
