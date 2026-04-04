import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from admin_router import router as admin_router
from config import get_settings
from host_tenant import subdomain_from_host as host_subdomain
from products_router import router as products_router
from settings_router import router as settings_router

POOL: asyncpg.Pool | None = None
MIGRATE_POOL: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global POOL, MIGRATE_POOL

    if os.getenv("TESTING") == "1":
        app.state.db_pool = None
        app.state.migrate_pool = None
        yield
        return

    settings = get_settings()
    app.state.settings = settings

    dsn = settings.normalize_dsn(settings.database_url)
    POOL = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
    app.state.db_pool = POOL

    mig = settings.migrate_database_url
    if mig:
        MIGRATE_POOL = await asyncpg.create_pool(settings.normalize_dsn(mig), min_size=1, max_size=5)
        app.state.migrate_pool = MIGRATE_POOL
    else:
        MIGRATE_POOL = None
        app.state.migrate_pool = None

    yield

    if MIGRATE_POOL:
        await MIGRATE_POOL.close()
        MIGRATE_POOL = None
    if POOL:
        await POOL.close()
        POOL = None
    app.state.db_pool = None
    app.state.migrate_pool = None


def _cors_from_settings() -> tuple[list[str], bool]:
    s = get_settings()
    origins = s.cors_origins_list()
    return origins, origins != ["*"]


_origins, _credentials = _cors_from_settings()

app = FastAPI(title="Shopper API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tenant_context(request: Request, call_next):
    settings = getattr(request.app.state, "settings", None) or get_settings()
    sub = host_subdomain(
        request.headers.get("host", ""),
        platform_root_domain=settings.platform_root_domain,
    )
    request.state.tenant_subdomain = sub
    response = await call_next(request)
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(products_router)
app.include_router(settings_router)
app.include_router(admin_router)
