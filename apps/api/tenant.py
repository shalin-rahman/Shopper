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


async def resolve_tenant_id(pool: asyncpg.Pool, subdomain: str) -> UUID:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM platform.tenants WHERE subdomain = $1 AND status = 'active'",
            subdomain,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Unknown or inactive tenant")
    return row["id"]


@asynccontextmanager
async def tenant_transaction(
    pool: asyncpg.Pool, tenant_id: UUID
) -> AsyncIterator[asyncpg.Connection]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant_id))
            yield conn
