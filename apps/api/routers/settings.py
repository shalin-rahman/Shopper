from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from schemas import TenantSettingsOut
from core.tenant_context import TenantCtxDep
from core.dependencies import ManagerDep

router = APIRouter(prefix="/v1/tenant/settings", tags=["settings"])


def _pool(ctx: TenantCtxDep) -> asyncpg.Pool:
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


def _row_to_out(row: asyncpg.Record) -> TenantSettingsOut:
    d = dict(row)
    if d.get("default_vat_rate_pct") is not None:
        d["default_vat_rate_pct"] = Decimal(str(d["default_vat_rate_pct"]))
    if d.get("module_access") is not None and not isinstance(d["module_access"], dict):
        d["module_access"] = dict(d["module_access"])
    return TenantSettingsOut(**d)


@router.get("", response_model=TenantSettingsOut)
async def get_tenant_settings(ctx: TenantCtxDep, _auth: ManagerDep):
    from core.config import get_settings
    settings = get_settings()

    if not ctx.subdomain:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    if ctx.dedicated_db is None and settings.testing:  # mocked
        from datetime import datetime
        return TenantSettingsOut(
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            theme_id="default",
            logo_url=None,
            legal_title_en="Shopper Demo",
            legal_title_bn="শপার ডেমো",
            bin="123456789-0101",
            default_language="en",
            default_vat_rate_pct=Decimal("15.0"),
            module_access={"pos": True, "inventory": True},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, theme_id, default_language, logo_url,
                   legal_title_en, legal_title_bn, bin, default_vat_rate_pct,
                   module_access, created_at, updated_at,
                   sslcommerz_store_id, sslcommerz_store_password,
                   bkash_app_key, bkash_app_secret, bkash_username, bkash_password,
                   nagad_merchant_id, nagad_public_key, nagad_private_key
            FROM platform.tenant_settings
            WHERE ctx.tenant_id = $1
            """,
            tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Tenant settings not provisioned")
    return _row_to_out(row)
