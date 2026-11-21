from __future__ import annotations
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import asyncpg
from fastapi import APIRouter, HTTPException
from schemas import TenantSettingsOut, TenantSettingsUpdate
from core.tenant_context import TenantCtxDep
from core.dependencies import ManagerDep, SettingsDep, StaffDep

router = APIRouter(prefix="/v1/tenant/settings", tags=["settings"])

_COLUMNS = (
    "tenant_id, theme_id, default_language, logo_url, legal_title_en, legal_title_bn, "
    "bin, default_vat_rate_pct, module_access, created_at, updated_at"
)
# These columns are NOT NULL in platform.tenant_settings.
_REQUIRED = ("theme_id", "default_language", "default_vat_rate_pct", "module_access")

def _row_to_out(row: asyncpg.Record) -> TenantSettingsOut:
    d = dict(row)
    if d.get("default_vat_rate_pct") is not None:
        d["default_vat_rate_pct"] = Decimal(str(d["default_vat_rate_pct"]))
    # The pool has no JSONB codec, so asyncpg returns the column as text.
    if isinstance(d.get("module_access"), str):
        d["module_access"] = json.loads(d["module_access"])
    return TenantSettingsOut(**d)

@router.get("", response_model=TenantSettingsOut)
async def get_tenant_settings(ctx: TenantCtxDep, _auth: StaffDep, settings: SettingsDep):
    if not ctx.subdomain:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")
    if ctx.dedicated_db is None and settings.testing:  # mocked
        return TenantSettingsOut(tenant_id=UUID("00000000-0000-0000-0000-000000000000"), theme_id="default", logo_url=None, legal_title_en="Shopper Demo", legal_title_bn="শপার ডেমো", bin="123456789-0101", default_language="en", default_vat_rate_pct=Decimal("15.0"), module_access={"pos": True, "inventory": True}, created_at=datetime.now(), updated_at=datetime.now())
    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            f"SELECT {_COLUMNS} FROM platform.tenant_settings WHERE tenant_id = $1",
            ctx.tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Tenant settings not provisioned")
    return _row_to_out(row)

@router.patch("", response_model=TenantSettingsOut)
async def update_tenant_settings(ctx: TenantCtxDep, body: TenantSettingsUpdate, _auth: ManagerDep, settings: SettingsDep):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return await get_tenant_settings(ctx, _auth, settings)
    cleared = [key for key in _REQUIRED if key in fields and fields[key] is None]
    if cleared:
        raise HTTPException(status_code=422, detail=f"These settings cannot be empty: {', '.join(cleared)}")
    if "module_access" in fields:
        fields["module_access"] = json.dumps(fields["module_access"])

    # updated_at is set by the table's touch trigger.
    set_parts = [
        f"{key} = ${index + 1}::jsonb" if key == "module_access" else f"{key} = ${index + 1}"
        for index, key in enumerate(fields)
    ]
    args = [*fields.values(), ctx.tenant_id]
    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            f"UPDATE platform.tenant_settings SET {', '.join(set_parts)} "
            f"WHERE tenant_id = ${len(args)} RETURNING {_COLUMNS}",
            *args,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Tenant settings not provisioned")
    return _row_to_out(row)
