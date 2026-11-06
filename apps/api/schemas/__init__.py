"""Pydantic schemas — split by domain, re-exported for backwards compatibility."""
from schemas.common import parse_date, FormattedDate
from schemas.product import ProductBase, ProductCreate, ProductUpdate, ProductOut
from schemas.customer import (
    CustomerBase, CustomerCreate, CustomerUpdate, CustomerOut,
    CustomerCollectionCreate, CustomerCollectionOut,
)
from schemas.invoice import (
    InvoiceLineBase, InvoiceLineCreate, InvoiceLineOut,
    InvoiceCreate, InvoiceOut, SalesReturnCreate, SalesReturnLineCreate, CreditNoteOut,
    CheckoutLinkOut,
)
from schemas.payment import PaymentGateway, PaymentCreate, PaymentOut, PaymentRefundCreate, PaymentReviewOut, PaymentReviewResolve
from schemas.report import (
    InventoryAgingBucket, InventoryAgingItem, InventoryAgingReportOut,
    StockValuationItem, StockValuationReportOut,
    VatRegisterLineOut, VatRegisterReportOut, BusinessAnalyticsOut,
)
from schemas.storefront import StorefrontProductOut, StorefrontProductListResponse
from schemas.tenant import TenantSettingsOut, TenantSettingsInternalOut, TenantSettingsUpdate
from schemas.procurement import (
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
    "InvoiceCreate", "InvoiceOut", "SalesReturnCreate", "SalesReturnLineCreate", "CreditNoteOut",
    "CheckoutLinkOut",
    "PaymentGateway", "PaymentCreate", "PaymentOut", "PaymentRefundCreate", "PaymentReviewOut", "PaymentReviewResolve",
    "InventoryAgingBucket", "InventoryAgingItem", "InventoryAgingReportOut",
    "StockValuationItem", "StockValuationReportOut",
    "VatRegisterLineOut", "VatRegisterReportOut", "BusinessAnalyticsOut",
    "StorefrontProductOut", "StorefrontProductListResponse",
    "TenantSettingsOut", "TenantSettingsInternalOut", "TenantSettingsUpdate",
    "DebitNoteOut", "PurchaseReturnCreate",
    "SupplierBase", "SupplierCreate", "SupplierOut",
    "POLineBase", "POLineCreate", "POLineOut", "POCreate", "POOut",
    "SupplierPaymentCreate", "SupplierPaymentOut",
]
