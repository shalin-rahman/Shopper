"""Platform Super Admin (shopper_migrate bypasses RLS). Guard with SHOPPER_ADMIN_API_KEY."""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from config import Settings
from deps import SettingsDep

router = APIRouter(prefix="/v1/admin", tags=["admin"])

_DB_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class TenantStatusBody(BaseModel):
    status: Literal["pending", "active", "suspended", "deleted"]


class ProvisionDedicatedDBBody(BaseModel):
    tenant_id: UUID
    database_name: str  # e.g., tenant_{subdomain}


@router.post("/tenants/provision-db")
async def provision_dedicated_db(
    request: Request,
    body: ProvisionDedicatedDBBody,
    settings: SettingsDep,
    x_shopper_admin_key: str | None = Header(default=None, alias="X-Shopper-Admin-Key"),
):
    _require_admin(x_shopper_admin_key, settings)
    pool = _migrate_pool(request)
    if pool is None:
        raise HTTPException(status_code=503, detail="Migrate database pool not configured")

    # Placeholder: create DB, run schema init, update tenant record
    # In production, use a separate admin connection or script
    async with pool.acquire() as conn:
        # Check if tenant exists
        tenant = await conn.fetchrow(
            "SELECT id, subdomain FROM platform.tenants WHERE id = $1",
            body.tenant_id,
        )
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        db_name = body.database_name.strip().lower()
        if not _DB_NAME_RE.fullmatch(db_name):
            raise HTTPException(
                status_code=400,
                detail="database_name must match ^[a-z][a-z0-9_]{0,62}$",
            )
        try:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
        except asyncpg.exceptions.DuplicateDatabaseError:
            pass  # Already exists

        # Update tenant
        await conn.execute(
            "UPDATE platform.tenants SET dedicated_database_name = $1 WHERE id = $2",
            db_name,
            body.tenant_id,
        )

    return {"status": "provisioned", "database": db_name}


def _migrate_pool(request: Request) -> asyncpg.Pool | None:
    return getattr(request.app.state, "migrate_pool", None)


def _require_admin(x_shopper_admin_key: str | None, settings: Settings) -> None:
    expected = (settings.shopper_admin_api_key or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin API disabled (set SHOPPER_ADMIN_API_KEY)")
    if not x_shopper_admin_key or x_shopper_admin_key != expected:
        raise HTTPException(status_code=401, detail="Invalid admin key")


@router.get("/tenants")
async def list_tenants(
    request: Request,
    settings: SettingsDep,
    x_shopper_admin_key: str | None = Header(default=None, alias="X-Shopper-Admin-Key"),
):
    _require_admin(x_shopper_admin_key, settings)
    pool = _migrate_pool(request)
    if pool is None:
        raise HTTPException(status_code=503, detail="Migrate database pool not configured")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, subdomain, display_name_en, display_name_bn, status,
                   dedicated_database_name, created_at, updated_at
            FROM platform.tenants
            ORDER BY subdomain
            """
        )
    return {"items": [dict(r) for r in rows]}


@router.patch("/tenants/{tenant_id}/status")
async def set_tenant_status(
    request: Request,
    tenant_id: UUID,
    body: TenantStatusBody,
    settings: SettingsDep,
    x_shopper_admin_key: str | None = Header(default=None, alias="X-Shopper-Admin-Key"),
):
    _require_admin(x_shopper_admin_key, settings)
    pool = _migrate_pool(request)
    if pool is None:
        raise HTTPException(status_code=503, detail="Migrate database pool not configured")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE platform.tenants
            SET status = $2, updated_at = now()
            WHERE id = $1
            RETURNING id, subdomain, display_name_en, display_name_bn, status,
                      dedicated_database_name, created_at, updated_at
            """,
            tenant_id,
            body.status,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return dict(row)
