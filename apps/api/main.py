from contextlib import asynccontextmanager
import contextvars
import logging
import json

import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from admin_router import router as admin_router
from config import get_settings
from redis_client import close_redis, connect_redis
from customers_router import router as customers_router
from host_tenant import subdomain_from_host as host_subdomain

tenant_id_ctx = contextvars.ContextVar("tenant_id", default="unknown")
trace_id_ctx = contextvars.ContextVar("trace_id", default="unknown")


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.tenant_id = tenant_id_ctx.get()
        record.trace_id = trace_id_ctx.get()
        return True
from payments_router import router as payments_router
from products_router import router as products_router
from reports_router import router as reports_router
from settings_router import router as settings_router
from storefront_router import router as storefront_router

POOL: asyncpg.Pool | None = None
MIGRATE_POOL: asyncpg.Pool | None = None
REDIS = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global POOL, MIGRATE_POOL, REDIS

    # Configure structured JSON logging with tenant and trace context
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(json.dumps({
        "timestamp": "%(asctime)s",
        "level": "%(levelname)s",
        "message": "%(message)s",
        "tenant_id": "%(tenant_id)s",
        "trace_id": "%(trace_id)s"
    }), datefmt="%Y-%m-%dT%H:%M:%SZ"))
    handler.addFilter(RequestContextFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]

    settings = get_settings()
    app.state.settings = settings

    if settings.testing:
        app.state.db_pool = None
        app.state.migrate_pool = None
        app.state.redis = None
        yield
        return

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

    REDIS = await connect_redis(settings.redis_url)
    app.state.redis = REDIS

    yield

    await close_redis(app.state.redis)
    REDIS = None
    app.state.redis = None

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
    import uuid
    trace_id = str(uuid.uuid4())
    trace_id_ctx.set(trace_id)

    settings = getattr(request.app.state, "settings", None) or get_settings()
    sub = host_subdomain(
        request.headers.get("host", ""),
        platform_root_domain=settings.platform_root_domain,
    )
    tenant_id_ctx.set(sub or "unknown")
    request.state.trace_id = trace_id
    request.state.tenant_subdomain = sub
    response = await call_next(request)
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(products_router)
app.include_router(settings_router)
app.include_router(admin_router)
app.include_router(payments_router)
app.include_router(reports_router)
app.include_router(customers_router)
app.include_router(storefront_router)
