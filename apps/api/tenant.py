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
    from .db import get_tenant_pool
    pool = await get_tenant_pool(request, dedicated_db)
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Choose isolation strategy based on configuration
            from .config import get_settings
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
