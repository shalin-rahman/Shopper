from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from schemas import TenantSettingsOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction

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
async def get_tenant_settings(request: Request):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required (Host or X-Shopper-Tenant)")

    pool = _pool(request)
    tenant_id: UUID = await resolve_tenant_id(pool, sub)
    async with tenant_transaction(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, theme_id, default_language, logo_url,
                   legal_title_en, legal_title_bn, bin, default_vat_rate_pct,
                   module_access, created_at, updated_at
            FROM platform.tenant_settings
            WHERE tenant_id = $1
            """,
            tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Tenant settings not provisioned")
    return _row_to_out(row)
