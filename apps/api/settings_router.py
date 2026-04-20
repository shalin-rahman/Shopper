from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from schemas import TenantSettingsOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from deps import ManagerDep

router = APIRouter(prefix="/v1/tenant/settings", tags=["settings"])


def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
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
async def get_tenant_settings(request: Request, _auth: ManagerDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required (Host or X-Shopper-Tenant)")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, theme_id, default_language, logo_url,
                   legal_title_en, legal_title_bn, bin, default_vat_rate_pct,
                   module_access, created_at, updated_at,
                   sslcommerz_store_id, sslcommerz_store_password,
                   bkash_app_key, bkash_app_secret, bkash_username, bkash_password,
                   nagad_merchant_id, nagad_public_key, nagad_private_key
            FROM platform.tenant_settings
            WHERE tenant_id = $1
            """,
            tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Tenant settings not provisioned")
    return _row_to_out(row)
