from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

import asyncpg
from fastapi import HTTPException, Request


def subdomain_from_request(request: Request) -> str | None:
    raw = (request.headers.get("X-Shopper-Tenant") or "").strip().lower()
    if raw:
        return raw
    return getattr(request.state, "tenant_subdomain", None)


async def resolve_tenant_id(pool: asyncpg.Pool, subdomain: str) -> dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, dedicated_database_name FROM platform.tenants WHERE subdomain = $1 AND status = 'active'",
            subdomain,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Unknown or inactive tenant")
    return dict(row)


@asynccontextmanager
async def tenant_transaction(
    request: Request, tenant_id: UUID, dedicated_db: str | None = None
) -> AsyncIterator[asyncpg.Connection]:
    from core.db import get_tenant_pool
    pool = await get_tenant_pool(request, dedicated_db)
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Choose isolation strategy based on configuration
            from core.config import get_settings
            settings = get_settings()
            if settings.tenant_isolation_mode == "schema":
                # Assume a schema named after the tenant UUID exists
                schema_name = f"tenant_{tenant_id}"
                await conn.execute(f'SET search_path = "{schema_name}"')
            else:
                # Default RLS approach
                await conn.execute(
                    "SELECT set_config('app.tenant_id', $1, true)",
                    str(tenant_id),
                )
            yield conn

from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends

from core.dependencies import SettingsDep

@dataclass
class TenantCtx:
    tenant_id: UUID
    subdomain: str
    dedicated_db: str | None
    request: Request

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        async with tenant_transaction(self.request, self.tenant_id, self.dedicated_db) as conn:
            yield conn

async def resolve_tenant_ctx(request: Request, settings: SettingsDep) -> TenantCtx:
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")
    pool = request.app.state.db_pool
    if pool is None:
        if settings.testing:
            return TenantCtx(tenant_id=UUID(int=0), subdomain=sub, dedicated_db=None, request=request)
        raise HTTPException(status_code=503, detail="Database unavailable")
    tenant = await resolve_tenant_id(pool, sub)
    return TenantCtx(
        tenant_id=tenant["id"],
        subdomain=sub,
        dedicated_db=tenant.get("dedicated_database_name"),
        request=request,
    )

TenantCtxDep = Annotated[TenantCtx, Depends(resolve_tenant_ctx)]
