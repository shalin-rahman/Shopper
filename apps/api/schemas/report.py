from __future__ import annotations
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel
from schemas.common import FormattedDate

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
