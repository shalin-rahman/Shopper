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
    status: Literal["pending", "active", "suspended", "deleted", "trialing", "past_due", "canceled"]


class ProvisionDedicatedDBBody(BaseModel):
    tenant_id: UUID
    database_name: str  # e.g., tenant_{subdomain}


class MigrateTenantBody(BaseModel):
    tenant_id: UUID
    source_db: str | None = None  # None for main DB
    target_db: str


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


@router.post("/tenants/migrate")
async def migrate_tenant(
    request: Request,
    body: MigrateTenantBody,
    settings: SettingsDep,
    x_shopper_admin_key: str | None = Header(default=None, alias="X-Shopper-Admin-Key"),
):
    _require_admin(x_shopper_admin_key, settings)
    from migration_service import migrate_to_dedicated
    
    success = await migrate_to_dedicated(
        request, 
        body.tenant_id, 
        body.source_db, 
        body.target_db
    )
    
    return {"status": "migrated" if success else "failed"}


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

@router.get("/tenants/{tenant_id}/export")
async def export_tenant_data(
    request: Request,
    tenant_id: UUID,
    settings: SettingsDep,
    x_shopper_admin_key: str | None = Header(default=None, alias="X-Shopper-Admin-Key"),
):
    """
    Consolidates ALL data for a tenant into a single portable JSON structure.
    Used for secure offboarding or legal portability requests.
    """
    _require_admin(x_shopper_admin_key, settings)
    pool = _migrate_pool(request)
    if pool is None:
        raise HTTPException(status_code=503, detail="Migrate database pool not configured")

    async with pool.acquire() as conn:
        tenant = await conn.fetchrow("SELECT * FROM platform.tenants WHERE id = $1", tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        export_body = {
            "tenant_meta": dict(tenant),
            "data": {}
        }
        
        tables = [
            "customers", "product_categories", "products", 
            "invoices", "invoice_lines", "payments", 
            "stock_transactions", "vat_sales_register_lines"
        ]
        
        for table in tables:
            rows = await conn.fetch(
                f"SELECT * FROM tenant_data.{table} WHERE tenant_id = $1", 
                tenant_id
            )
            export_body["data"][table] = [dict(r) for r in rows]
            
    return export_body


@router.post("/cron/dunning")
async def run_dunning_cron(
    request: Request,
    settings: SettingsDep,
    x_shopper_admin_key: str | None = Header(default=None, alias="X-Shopper-Admin-Key"),
):
    """
    SaaS Billing Platform Automation:
    1. Identifies tenants whose trial is over -> transitions to 'past_due' (Day 0)
    2. Identifies tenants in 'past_due' for > 14 days -> transitions to 'suspended' (Day 14)
    Suspended tenants automatically lose database access / API token validation.
    """
    _require_admin(x_shopper_admin_key, settings)
    pool = _migrate_pool(request)
    if pool is None:
        raise HTTPException(status_code=503, detail="Migrate database pool not configured")

    actions = {"past_due": [], "suspended": []}

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Rule 1: Trial expired -> Past Due
            rows_past_due = await conn.fetch(
                """
                UPDATE platform.tenants
                SET status = 'past_due', updated_at = now(), last_payment_failed_at = now()
                WHERE status = 'trialing' AND trial_ends_at < now()
                RETURNING id, subdomain
                """
            )
            actions["past_due"] = [r["subdomain"] for r in rows_past_due]

            # Rule 2: Past Due longer than 14 days -> Suspended (Locks down access)
            rows_suspended = await conn.fetch(
                """
                UPDATE platform.tenants
                SET status = 'suspended', updated_at = now()
                WHERE status = 'past_due' 
                  AND last_payment_failed_at < now() - interval '14 days'
                RETURNING id, subdomain
                """
            )
            actions["suspended"] = [r["subdomain"] for r in rows_suspended]

    return {"status": "success", "processed_actions": actions}

