from __future__ import annotations
import asyncpg
from fastapi import Request, HTTPException
from yarl import URL
from config import get_settings

DEDICATED_POOLS: dict[str, asyncpg.Pool] = {}

def get_main_pool(request: Request) -> asyncpg.Pool:
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Principal database unavailable")
    return pool

async def get_tenant_pool(request: Request, db_name: str | None) -> asyncpg.Pool:
    if not db_name:
        return get_main_pool(request)

    global DEDICATED_POOLS
    if db_name in DEDICATED_POOLS:
        return DEDICATED_POOLS[db_name]

    settings = get_settings()
    base_dsn = settings.normalize_dsn(settings.database_url)
    
    url = URL(base_dsn)
    dedicated_url = url.with_path(f"/{db_name}")
    
    new_pool = await asyncpg.create_pool(str(dedicated_url), min_size=1, max_size=10)
    DEDICATED_POOLS[db_name] = new_pool
    return new_pool

async def close_all_pools(app_state):
    global DEDICATED_POOLS
    for dp in DEDICATED_POOLS.values():
        await dp.close()
    DEDICATED_POOLS = {}
    
    if hasattr(app_state, "db_pool") and app_state.db_pool:
        await app_state.db_pool.close()
    if hasattr(app_state, "migrate_pool") and app_state.migrate_pool:
        await app_state.migrate_pool.close()
