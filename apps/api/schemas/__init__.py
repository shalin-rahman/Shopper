"""Pydantic schemas — split by domain, re-exported for backwards compatibility."""
from schemas.common import parse_date, FormattedDate
from schemas.product import ProductBase, ProductCreate, ProductUpdate, ProductOut
from schemas.customer import (
    CustomerBase, CustomerCreate, CustomerUpdate, CustomerOut,
    CustomerCollectionCreate, CustomerCollectionOut,
)
from schemas.invoice import (
    InvoiceLineBase, InvoiceLineCreate, InvoiceLineOut,
    InvoiceCreate, InvoiceOut, SalesReturnCreate, CreditNoteOut,
)
from schemas.payment import PaymentGateway, PaymentCreate, PaymentOut
from schemas.report import (
    InventoryAgingBucket, InventoryAgingItem, InventoryAgingReportOut,
    StockValuationItem, StockValuationReportOut,
    VatRegisterLineOut, VatRegisterReportOut, BusinessAnalyticsOut,
)
from schemas.storefront import StorefrontProductOut, StorefrontProductListResponse
from schemas.tenant import TenantSettingsOut, TenantSettingsInternalOut
from schemas.procurement import (
    InventoryTransferCreate, InventoryTransferOut,
    DebitNoteOut, PurchaseReturnCreate,
    SupplierBase, SupplierCreate, SupplierOut,
    POLineBase, POLineCreate, POLineOut, POCreate, POOut,
    SupplierPaymentCreate, SupplierPaymentOut,
)

__all__ = [
    "parse_date", "FormattedDate",
    "ProductBase", "ProductCreate", "ProductUpdate", "ProductOut",
    "CustomerBase", "CustomerCreate", "CustomerUpdate", "CustomerOut",
    "CustomerCollectionCreate", "CustomerCollectionOut",
    "InvoiceLineBase", "InvoiceLineCreate", "InvoiceLineOut",
    "InvoiceCreate", "InvoiceOut", "SalesReturnCreate", "CreditNoteOut",
    "PaymentGateway", "PaymentCreate", "PaymentOut",
    "InventoryAgingBucket", "InventoryAgingItem", "InventoryAgingReportOut",
    "StockValuationItem", "StockValuationReportOut",
    "VatRegisterLineOut", "VatRegisterReportOut", "BusinessAnalyticsOut",
    "StorefrontProductOut", "StorefrontProductListResponse",
    "TenantSettingsOut", "TenantSettingsInternalOut",
    "InventoryTransferCreate", "InventoryTransferOut",
    "DebitNoteOut", "PurchaseReturnCreate",
    "SupplierBase", "SupplierCreate", "SupplierOut",
    "POLineBase", "POLineCreate", "POLineOut", "POCreate", "POOut",
    "SupplierPaymentCreate", "SupplierPaymentOut",
]
