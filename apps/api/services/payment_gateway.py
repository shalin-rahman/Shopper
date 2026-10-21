from __future__ import annotations
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID
import asyncpg
from fastapi import HTTPException, Request
import httpx
from core.config import Settings
from schemas import PaymentCreate, PaymentGateway, PaymentOut, TenantSettingsInternalOut
from core.tenant_context import tenant_transaction

class PaymentGatewayInterface(ABC):
    @abstractmethod
    async def initiate_payment(
        self,
        payment: PaymentCreate,
        tenant_subdomain: str,
        settings: Settings,
        tenant_settings: TenantSettingsInternalOut,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def verify_ipn(
        self,
        ipn_data: dict[str, Any],
        settings: Settings,
        tenant_settings: TenantSettingsInternalOut,
    ) -> dict[str, Any] | None:
        pass

    def ipn_payment_status(self, ipn_data: dict[str, Any]) -> str:
        return "pending"

class SSLCommerzGateway(PaymentGatewayInterface):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def initiate_payment(self, payment: PaymentCreate, tenant_subdomain: str, settings: Settings, tenant_settings: TenantSettingsInternalOut) -> dict[str, Any]:
        store_id = tenant_settings.sslcommerz_store_id or settings.sslcommerz_store_id
        store_pass = tenant_settings.sslcommerz_store_password or settings.sslcommerz_store_password
        if not store_id or not store_pass:
            raise HTTPException(status_code=400, detail=f"SSLCommerz credentials not configured for tenant {tenant_subdomain}")
        is_sandbox = str(store_id).lower().startswith("test")
        base_url = "https://sandbox.sslcommerz.com" if is_sandbox else "https://securepay.sslcommerz.com"
        api_url = f"{base_url}/gwprocess/v4/api.php"
        storefront_url = settings.storefront_public_base_url or f"https://{tenant_subdomain}.shopper.com"
        api_base = settings.platform_root_domain or "https://api.shopper.com"
        ipn_url = f"{api_base}/v1/tenant/payments/ipn/sslcommerz?tenant={tenant_subdomain}"
        payload = {
            "store_id": store_id, "store_passwd": store_pass, "total_amount": float(payment.amount),
            "currency": payment.currency, "tran_id": payment.order_id or str(UUID(int=0)),
            "success_url": f"{storefront_url}/checkout/success", "fail_url": f"{storefront_url}/checkout/fail",
            "cancel_url": f"{storefront_url}/checkout/cancel", "ipn_url": ipn_url,
            "cus_name": tenant_settings.legal_title_en or tenant_subdomain, "cus_email": "customer@example.com",
            "cus_add1": tenant_settings.legal_title_bn or "Bangladesh", "cus_phone": "01700000000",
            "shipping_method": "NO", "product_name": payment.description or "Shopper Order",
            "product_category": "Retail", "product_profile": "general",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(api_url, data=payload)
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") != "SUCCESS":
            raise HTTPException(status_code=502, detail=f"SSLCommerz error: {data.get('failedreason', 'Unknown error')}")
        return {"gateway_url": data["GatewayPageURL"], "sessionkey": data["sessionkey"]}

    async def verify_ipn(
        self,
        ipn_data: dict[str, Any],
        settings: Settings,
        tenant_settings: TenantSettingsInternalOut,
    ) -> dict[str, Any] | None:
        store_id = tenant_settings.sslcommerz_store_id or settings.sslcommerz_store_id
        store_pass = tenant_settings.sslcommerz_store_password or settings.sslcommerz_store_password
        if not store_id or not store_pass:
            return None
        if str(ipn_data.get("store_id") or "").strip() != str(store_id).strip():
            return None
        val_id = ipn_data.get("val_id")
        if not val_id:
            return None
        is_sandbox = str(store_id).lower().startswith("test")
        base_url = "https://sandbox.sslcommerz.com" if is_sandbox else "https://securepay.sslcommerz.com"
        api_url = f"{base_url}/validator/api/validationserverAPI.php"
        params = {"val_id": val_id, "store_id": store_id, "store_passwd": store_pass, "format": "json"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(api_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail="SSLCommerz verification service is unavailable",
            ) from exc

        if not isinstance(data, dict) or data.get("status") not in ("VALID", "VALIDATED"):
            return None

        provider_order_id = str(data.get("tran_id") or "").strip()
        provider_transaction_id = str(data.get("val_id") or "").strip()
        provider_currency = str(data.get("currency") or "").strip().upper()
        try:
            provider_amount = Decimal(str(data.get("amount")))
        except (InvalidOperation, TypeError, ValueError):
            return None

        if (
            not provider_order_id
            or not provider_transaction_id
            or not provider_currency
            or not provider_amount.is_finite()
            or provider_amount <= 0
        ):
            return None

        callback_order_id = str(ipn_data.get("tran_id") or "").strip()
        callback_amount = ipn_data.get("amount")
        callback_currency = str(ipn_data.get("currency") or "").strip().upper()
        if callback_order_id and callback_order_id != provider_order_id:
            return None
        if callback_amount not in (None, ""):
            try:
                if Decimal(str(callback_amount)) != provider_amount:
                    return None
            except (InvalidOperation, TypeError, ValueError):
                return None
        if callback_currency and callback_currency != provider_currency:
            return None

        return {
            "tran_id": provider_order_id,
            "val_id": provider_transaction_id,
            "amount": provider_amount,
            "currency": provider_currency,
            "status": "VALIDATED",
        }

    def ipn_payment_status(self, ipn_data: dict[str, Any]) -> str:
        st = str(ipn_data.get("status") or "").strip().upper()
        return "completed" if st in ("VALID", "VALIDATED") else "failed"

class BKashGateway(PaymentGatewayInterface):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def initiate_payment(self, payment: PaymentCreate, tenant_subdomain: str, settings: Settings, tenant_settings: TenantSettingsInternalOut) -> dict[str, Any]:
        raise HTTPException(
            status_code=503,
            detail="bKash payments are unavailable until provider verification is configured",
        )

    async def verify_ipn(self, ipn_data: dict[str, Any], settings: Settings, tenant_settings: TenantSettingsInternalOut) -> dict[str, Any] | None:
        raise HTTPException(
            status_code=503,
            detail="bKash payments are unavailable until provider verification is configured",
        )

class NagadGateway(PaymentGatewayInterface):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def initiate_payment(self, payment: PaymentCreate, tenant_subdomain: str, settings: Settings, tenant_settings: TenantSettingsInternalOut) -> dict[str, Any]:
        raise HTTPException(
            status_code=503,
            detail="Nagad payments are unavailable until provider verification is configured",
        )

    async def verify_ipn(self, ipn_data: dict[str, Any], settings: Settings, tenant_settings: TenantSettingsInternalOut) -> dict[str, Any] | None:
        raise HTTPException(
            status_code=503,
            detail="Nagad payments are unavailable until provider verification is configured",
        )

def get_gateway(gateway: PaymentGateway, settings: Settings) -> PaymentGatewayInterface:
    if gateway == PaymentGateway.sslcommerz: return SSLCommerzGateway(settings)
    if gateway == PaymentGateway.bkash: return BKashGateway(settings)
    if gateway == PaymentGateway.nagad: return NagadGateway(settings)
    raise HTTPException(status_code=501, detail=f"Gateway {gateway} not implemented")

async def get_tenant_settings(request: Request, tenant_id: UUID) -> TenantSettingsInternalOut:
    async with tenant_transaction(request, tenant_id) as conn:
        row = await conn.fetchrow("""
            SELECT tenant_id, theme_id, default_language, logo_url,
                   legal_title_en, legal_title_bn, bin, default_vat_rate_pct,
                   module_access, created_at, updated_at,
                   sslcommerz_store_id, sslcommerz_store_password,
                   bkash_app_key, bkash_app_secret, bkash_username, bkash_password,
                   nagad_merchant_id, nagad_public_key, nagad_private_key
            FROM platform.tenant_settings WHERE tenant_id = $1
        """, tenant_id)
    if not row: raise HTTPException(status_code=404, detail="Tenant settings not found")
    d = dict(row)
    if d.get("default_vat_rate_pct") is not None: d["default_vat_rate_pct"] = Decimal(str(d["default_vat_rate_pct"]))
    if d.get("module_access") is not None and not isinstance(d["module_access"], dict): d["module_access"] = dict(d["module_access"])
    return TenantSettingsInternalOut(**d)

def payment_row_to_out(row: asyncpg.Record) -> PaymentOut:
    d = dict(row)
    if d.get("amount") is not None: d["amount"] = Decimal(str(d["amount"]))
    d["gateway"] = PaymentGateway(d["gateway"])
    return PaymentOut(**d)
