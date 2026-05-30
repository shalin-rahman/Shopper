# Shopper Platform — Implementation-Ready Refactor Plan

## Executive Summary

The Shopper platform is a **multi-tenant retail/POS system** comprising a FastAPI backend (Python), an Angular web frontend, and a Flutter mobile POS app, backed by PostgreSQL with Row-Level Security and optional per-tenant databases, Redis for IPN idempotency, and OpenResty as a reverse proxy.

**Critical findings:**

1. **Hardcoded secrets** — JWT `SECRET_KEY` is duplicated as a literal in both `deps.py` and `auth_router.py`.
2. **Massive code duplication** — Every API router repeats the same 8-line tenant-resolution boilerplate. A `_pool()` helper is copy-pasted across 6 files. `_row_to_out` converters with identical Decimal-coercion logic exist in 5 routers.
3. **Broken relative imports** in `tenant.py` — Uses `from .db` and `from .config` (package-relative syntax) but the API is run as flat modules, not a package. This will crash at runtime for the `tenant_transaction` function.
4. **Duplicate, abandoned mobile app** — `apps/shopper-mobile/` is a dead shell; the real app is `shopper-mobile/`. Both have `pubspec.yaml` files. This is a maintenance trap.
5. **Monolithic schemas file** — All Pydantic models for every feature crammed into one 280-line `schemas.py`.
6. **Untyped POS endpoint** — `pos_router.py`'s `offline-punch` accepts `list[dict[str, Any]]` with zero validation, doing arithmetic on unvalidated `.get()` calls — a production crash waiting to happen.
7. **Mobile ↔ API contract mismatch** — The mobile `ApiClient` calls endpoints like `/v1/auth/login` (no `/tenant/` prefix), expects `refresh_token` and `expires_at` fields the API never returns, and has a Product model with 20+ fields the API doesn't serve.
8. **No shared type contract** — Web, mobile, and API each independently define Product/Order/Settings types with different field names, different nullability, and different serialization.
9. **Global mutable state** in `db.py` — `DEDICATED_POOLS` is a module-level dict mutated by async code with no locking, creating race conditions under concurrent tenant provisioning.
10. **Two contradictory task files** — `tasks.txt` (root) says everything is DONE; `docs/tasks.txt` says most things are TODO. No single source of truth.

---

## 1. Repo Audit

### 1.1 High-Level Architecture

```
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Angular Web │  │ Flutter POS  │  │ Public Storefront │
│ (admin/mgr) │  │ (cashier)    │  │ (customer-facing) │
└──────┬──────┘  └──────┬───────┘  └────────┬──────────┘
       │                │                    │
       └────────────────┴────────────────────┘
                        │
              ┌─────────▼──────────┐
              │  OpenResty (TLS +  │
              │  subdomain routing)│
              └─────────┬──────────┘
                        │
              ┌─────────▼──────────┐
              │  FastAPI Backend   │
              │  (12 router files) │
              └──┬──────────────┬──┘
                 │              │
         ┌───────▼───┐   ┌─────▼─────┐
         │ PostgreSQL │   │   Redis   │
         │ (RLS/multi │   │ (IPN de-  │
         │  -tenant)  │   │  dupe)    │
         └────────────┘   └───────────┘
```

### 1.2 Main Feature Areas

| Area | Files | Description |
|------|-------|-------------|
| **Tenant Resolution** | `host_tenant.py`, `tenant.py`, `db.py`, `main.py` middleware | Subdomain → tenant_id → RLS/schema/dedicated-DB routing |
| **Auth & RBAC** | `auth_router.py`, `deps.py` | JWT login, role-based deps (Staff/Accountant/Manager/Admin) |
| **Product Catalog** | `products_router.py`, `codes.py` | CRUD + barcode/QR generation |
| **Invoicing** | `invoices_router.py` | Create/list/get invoices, QR code, Mushak 6.3 PDF |
| **Payments** | `payments_router.py`, `payments_core.py` | Multi-gateway (SSLCommerz, bKash, Nagad), IPN processing |
| **POS** | `pos_router.py`, `receipt_router.py` | Offline sync, thermal receipt rendering |
| **Reports** | `reports_router.py` | Inventory aging, stock valuation (WAC), VAT register |
| **Storefront** | `storefront_router.py` | Public catalog, checkout, payment initiation |
| **Admin** | `admin_router.py`, `migration_service.py` | Tenant lifecycle, DB provisioning, data migration |
| **Web Frontend** | `apps/shopper-web/src/` | Angular 17+ standalone components, Transloco i18n, theming |
| **Mobile POS** | `shopper-mobile/lib/` | Flutter with BLoC, clean architecture (domain/data/core layers) |

### 1.3 Core Dependencies & Coupling Points

| Dependency | Used By | Coupling Level |
|------------|---------|----------------|
| `tenant.py` (resolve + transaction) | Every router (8 files) | **Very High** — identical 6-line boilerplate in each |
| `db.py` (pool access) | Every router via `_pool()` copy-paste | **High** |
| `schemas.py` (all Pydantic models) | Every router + `payments_core.py` | **High** — single monolith file |
| `deps.py` (auth deps + settings) | Every authenticated router | **Medium** |
| `config.py` (Settings) | `deps.py`, `db.py`, `tenant.py`, `main.py`, `payments_core.py` | **Medium** |
| JWT SECRET_KEY | `auth_router.py` AND `deps.py` (duplicated literal) | **Critical** — drift risk |
| `payments_core.py` | `payments_router.py`, `storefront_router.py` | **Medium** |

### 1.4 Key Design Flaws & Risks

| # | Flaw | Severity | Location |
|---|------|----------|----------|
| F1 | Hardcoded JWT secret duplicated in 2 files | **CRITICAL** | `deps.py:15`, `auth_router.py:13` |
| F2 | `tenant.py` uses relative imports (`from .db`, `from .config`) in a flat-module project — will crash at runtime | **CRITICAL** | `tenant.py:35-38` |
| F3 | `DEDICATED_POOLS` global dict mutated without async lock | **HIGH** | `db.py:6-18` |
| F4 | `pos_router.offline_punch` accepts unvalidated `list[dict[str, Any]]` and does arithmetic on `.get()` | **HIGH** | `pos_router.py:27-95` |
| F5 | Payment credentials (bKash secret, Nagad private key) returned in `TenantSettingsOut` response | **HIGH** | `schemas.py:44-55` |
| F6 | Exception in `offline-punch` loop silently swallowed with `print()` | **HIGH** | `pos_router.py:92` |
| F7 | Mobile `ApiClient.baseUrl` is hardcoded `https://api.shopper.com/v1` | **HIGH** | `api_client.dart:18` |
| F8 | Duplicate dead mobile app at `apps/shopper-mobile/` | **MEDIUM** | Whole directory |
| F9 | `_row_to_out` Decimal-coercion pattern duplicated across 5+ routers | **MEDIUM** | Every router file |
| F10 | No web frontend tests except `app.component.spec.ts` and `theme.service.spec.ts` | **MEDIUM** | `apps/shopper-web/` |
| F11 | `invoices_router.py` imports `qrcode` and `reportlab` — PDF rendering tightly coupled to HTTP handler | **MEDIUM** | `invoices_router.py:8-10` |
| F12 | Mobile `OrdersBloc` imports non-existent `'../../../../core/usecases/usecase.dart'` (wrong path depth) | **MEDIUM** | `orders_bloc.dart:7` |
| F13 | Mobile ↔ API data contract mismatch (endpoints, field names, response shapes) | **HIGH** | `api_client.dart` vs all routers |

---

## 2. Modularization / Plugin Strategy

Given this is a multi-tenant SaaS with three consumers (web, mobile, API-internal), the right modular architecture is **layered service extraction** within the API, **shared DTO schemas** published as an OpenAPI contract, and **feature-module boundaries** within each frontend.

### 2.1 Proposed API Module Boundaries

```
apps/api/
├── core/                          # Shared infrastructure
│   ├── __init__.py
│   ├── config.py                  # Settings (current config.py)
│   ├── db.py                      # Pool management (with async lock fix)
│   ├── security.py                # JWT constants, password hashing (extracted)
│   ├── tenant_context.py          # Tenant resolution + transaction context manager
│   ├── dependencies.py            # All FastAPI Depends (current deps.py)
│   └── exceptions.py              # Custom exception classes
├── schemas/                       # Split by domain
│   ├── __init__.py
│   ├── product.py
│   ├── customer.py
│   ├── invoice.py
│   ├── payment.py
│   ├── report.py
│   ├── storefront.py
│   └── tenant.py
├── services/                      # Business logic extracted from routers
│   ├── __init__.py
│   ├── product_service.py
│   ├── invoice_service.py
│   ├── payment_gateway.py         # Current payments_core.py
│   ├── receipt_renderer.py        # Thermal receipt logic
│   ├── pdf_renderer.py            # Mushak PDF logic
│   ├── pos_service.py             # Offline punch orchestration
│   ├── report_service.py
│   └── migration_service.py
├── routers/                       # Thin HTTP handlers only
│   ├── __init__.py
│   ├── products.py
│   ├── customers.py
│   ├── invoices.py
│   ├── payments.py
│   ├── pos.py
│   ├── receipts.py
│   ├── reports.py
│   ├── settings.py
│   ├── storefront.py
│   ├── admin.py
│   └── auth.py
├── utils/
│   ├── __init__.py
│   ├── decimal_helpers.py         # row_to_dict with Decimal coercion
│   └── codes.py                   # Barcode/QR generation
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_codes.py
│   │   ├── test_host_tenant.py
│   │   ├── test_redis_client.py
│   │   ├── test_security.py
│   │   └── test_decimal_helpers.py
│   ├── integration/
│   │   ├── test_rls_isolation.py
│   │   ├── test_pos_e2e.py
│   │   └── test_billing.py
│   └── api/
│       ├── test_api_smoke.py
│       └── test_migration_pipeline.py
├── main.py
└── redis_client.py
```

### 2.2 Public Interfaces / Contracts

**TenantContext (core/tenant_context.py)** — replaces the boilerplate in every router:

```python
# Usage in any router:
async def list_products(ctx: TenantCtxDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT ...")
```

This single dependency would replace the repeated pattern of:
- `subdomain_from_request(request)`
- `_pool(request)`
- `resolve_tenant_id(pool, sub)`
- `tenant_transaction(request, tenant_id, dedicated_db)`

**DecimalRowMapper (utils/decimal_helpers.py)** — replaces 5 copies of `_row_to_out`:

```python
def row_to_dict(row: asyncpg.Record, decimal_fields: list[str]) -> dict:
    d = dict(row)
    for k in decimal_fields:
        if d.get(k) is not None:
            d[k] = Decimal(str(d[k]))
    return d
```

**PaymentGatewayInterface (services/payment_gateway.py)** — already exists; keep as-is but register gateways in a dict for plug-and-play:

```python
GATEWAY_REGISTRY: dict[PaymentGateway, type[PaymentGatewayInterface]] = {
    PaymentGateway.sslcommerz: SSLCommerzGateway,
    PaymentGateway.bkash: BKashGateway,
    PaymentGateway.nagad: NagadGateway,
}
```

### 2.3 Shared Core vs Feature-Specific Code

| Layer | Contents | Consumers |
|-------|----------|-----------|
| **core/** | Config, DB, Auth, Tenant resolution, Dependencies | All routers, all services |
| **schemas/** | Pydantic models (request/response) | Routers, services, tests |
| **services/** | Business logic (no HTTP knowledge) | Routers only |
| **routers/** | Thin HTTP wiring (parse → call service → return) | `main.py` registration |
| **utils/** | Decimal helpers, barcode generation | Services, routers |

### 2.4 Module Registration

Routers are registered in `main.py` via a list:

```python
ROUTERS = [
    ("routers.products", "router"),
    ("routers.auth", "router"),
    ...
]
for module_path, attr in ROUTERS:
    mod = importlib.import_module(module_path)
    app.include_router(getattr(mod, attr))
```

For gateway plugins, new gateways are added to `GATEWAY_REGISTRY` in `services/payment_gateway.py` — no router changes needed.

---

## 3. Phased Implementation Plan

### Phase 0: Pre-requisites & Safety Net (1-2 days)

**What changes:** Fix critical bugs that will cause runtime failures; add no new features.

| Step | Change | Files | Why | Risk |
|------|--------|-------|-----|------|
| 0.1 | Fix relative imports in `tenant.py` | `tenant.py` | `from .db` / `from .config` will crash — change to absolute imports `from db import ...` | **None** — purely corrective |
| 0.2 | Extract JWT secret to `config.py` as `Settings.jwt_secret_key` and `Settings.jwt_algorithm` | `config.py`, `deps.py`, `auth_router.py` | Eliminates duplicated hardcoded secret | **Low** — all tests still pass since `TESTING=1` skips DB |
| 0.3 | Delete `apps/shopper-mobile/` directory | `apps/shopper-mobile/` (2 files) | Dead code; real app is `shopper-mobile/` | **None** — directory is unused |
| 0.4 | Add `__pycache__` and `*.pyc` to `.gitignore` | `.gitignore` | Committed cache files in `apps/api/__pycache__/` | **None** |
| 0.5 | Fix `OrdersBloc` import path | `shopper-mobile/lib/core/bloc/orders/orders_bloc.dart:7` | `'../../../../core/usecases/usecase.dart'` has wrong depth — should be `'../../usecase/usecase.dart'` | **None** |
| 0.6 | Redact payment credentials from `TenantSettingsOut` | `schemas.py` (split sensitive fields into `TenantSettingsInternalOut`) | Private keys visible in API response | **Medium** — web frontend may reference missing fields; add separate admin-only endpoint |

**Tests impacted:** `test_api.py` (settings response shape may change), `test_billing.py`. Run full suite after.

**Rollback:** Each step is an independent commit; revert any commit individually.

---

### Phase 1: API Package Structure (2-3 days)

**What changes:** Convert the flat-file API into a proper Python package with `__init__.py` files. Move files into the directory structure from §2.1. All imports updated.

| Step | Change | Files Moved/Created | Compatibility |
|------|--------|---------------------|---------------|
| 1.1 | Create directory skeleton: `core/`, `schemas/`, `services/`, `routers/`, `utils/`, each with `__init__.py` | New dirs + `__init__.py` files | No behavior change |
| 1.2 | Move `config.py` → `core/config.py`, `db.py` → `core/db.py`, `deps.py` → `core/dependencies.py`, `tenant.py` → `core/tenant_context.py`, `host_tenant.py` → `core/host_tenant.py` | 5 files moved | Update all imports in routers + tests |
| 1.3 | Split `schemas.py` into `schemas/product.py`, `schemas/customer.py`, `schemas/invoice.py`, `schemas/payment.py`, `schemas/report.py`, `schemas/storefront.py`, `schemas/tenant.py`; re-export from `schemas/__init__.py` | 1 file → 8 files | Backwards compatible via `schemas/__init__.py` re-exports |
| 1.4 | Move routers: `products_router.py` → `routers/products.py`, etc. (12 files) | 12 files moved | Update `main.py` imports |
| 1.5 | Move `codes.py` → `utils/codes.py`, extract `decimal_helpers.py` | 1 moved, 1 new | Update `products_router`, `invoices_router`, `payments_router`, etc. |
| 1.6 | Move `redis_client.py` to root of package (stays) | No move needed | — |
| 1.7 | Move tests into `tests/unit/` and `tests/integration/` | 8 test files | Update `pytest.ini` testpaths |
| 1.8 | Update `Dockerfile` `WORKDIR` and `CMD` if needed | `apps/api/Dockerfile` | Verify `uvicorn main:app` still resolves |
| 1.9 | Update CI workflow path | `.github/workflows/ci.yml` | Ensure `pytest` discovers new test paths |

**Files touched:** Every `.py` file in `apps/api/` (import paths change). All test files.

**Rollback risk:** **Medium** — this is a large rename. Mitigate by doing it in a single PR with a passing CI gate. If CI breaks, revert the whole PR.

---

### Phase 2: Tenant Context Dependency (1-2 days)

**What changes:** Replace the 8-line tenant boilerplate in every router with a single `TenantCtxDep`.

**New file:** `core/tenant_context.py` additions

```python
@dataclass
class TenantCtx:
    tenant_id: UUID
    subdomain: str
    dedicated_db: str | None
    request: Request

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        # wraps existing tenant_transaction logic
        ...

async def resolve_tenant_ctx(request: Request) -> TenantCtx:
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(400, "Tenant subdomain required")
    pool = get_main_pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    return TenantCtx(
        tenant_id=tenant["id"],
        subdomain=sub,
        dedicated_db=tenant["dedicated_database_name"],
        request=request,
    )

TenantCtxDep = Annotated[TenantCtx, Depends(resolve_tenant_ctx)]
```

**Routers changed:** `products.py`, `customers.py`, `invoices.py`, `payments.py`, `pos.py`, `receipts.py`, `reports.py`, `settings.py`, `storefront.py` (9 routers). Each shrinks by ~5-8 lines per endpoint.

**Before:**
```python
async def list_products(request: Request, _auth: StaffDep):
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(...)
```

**After:**
```python
async def list_products(ctx: TenantCtxDep, _auth: StaffDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch(...)
```

**Tests impacted:** All router tests that mock tenant resolution. Update mock targets.

**Rollback:** Revert single PR. Old boilerplate pattern still works as fallback.

---

### Phase 3: Service Layer Extraction (3-4 days)

**What changes:** Move business logic out of routers into service modules. Routers become thin HTTP wiring.

| Service | Extracted From | Key Methods |
|---------|---------------|-------------|
| `services/product_service.py` | `routers/products.py` | `list_products(conn)`, `create_product(conn, body, settings)`, `update_product(conn, id, body)` |
| `services/invoice_service.py` | `routers/invoices.py` | `create_invoice(conn, body)`, `get_invoice(conn, id)` |
| `services/pdf_renderer.py` | `routers/invoices.py` (mushak PDF) | `render_mushak_pdf(invoice, lines, settings) -> bytes` |
| `services/receipt_renderer.py` | `routers/receipts.py` | `render_thermal_receipt(invoice, lines, settings, lang) -> str` |
| `services/pos_service.py` | `routers/pos.py` | `sync_offline_orders(conn, tenant_id, orders) -> SyncResult` |
| `services/report_service.py` | `routers/reports.py` | `inventory_aging(conn, as_of)`, `stock_valuation(conn)`, `vat_register(conn, start, end)` |

**Why:** Enables unit-testing business logic without HTTP. Enables reuse (e.g., `pdf_renderer` from both invoice router and a future batch-export job). Eliminates the tangle of `qrcode`/`reportlab` imports in HTTP handlers.

**Files impacted:** 6 new service files; 6 routers refactored; 6+ new unit test files for services.

**Compatibility:** No API contract change. All endpoints return identical responses.

---

### Phase 4: Fix POS Validation & DB Safety (1-2 days)

**What changes:**

| Step | Change | File |
|------|--------|------|
| 4.1 | Create Pydantic schemas for POS offline-punch: `OfflinePunchOrder`, `OfflinePunchItem` | `schemas/pos.py` (new) |
| 4.2 | Replace `body: list[dict[str, Any]]` with `body: list[OfflinePunchOrder]` | `routers/pos.py` |
| 4.3 | Replace `print()` in exception handler with `logger.exception()` and add per-order error accumulation | `services/pos_service.py` |
| 4.4 | Add `asyncio.Lock` around `DEDICATED_POOLS` access in `core/db.py` | `core/db.py` |
| 4.5 | Wrap mobile `ApiClient.baseUrl` in a configurable constant loaded from environment/build config | `shopper-mobile/lib/data/sources/remote/api_client.dart` |

**Tests:**
- New: `tests/unit/test_pos_schemas.py` — validate POS schema rejects missing fields
- Updated: `tests/integration/test_pos_e2e.py` — use valid schema payloads
- New: `tests/unit/test_db_pool_lock.py` — concurrent pool creation safety

---

### Phase 5: OpenAPI Contract & Frontend Alignment (2-3 days)

**What changes:**

| Step | Change | Files |
|------|--------|-------|
| 5.1 | Generate OpenAPI spec from FastAPI (`/openapi.json`), commit as `docs/openapi.json` | CI pipeline + `docs/` |
| 5.2 | Create a `ProductService` in Angular that matches actual API response shape (currently missing `stock_quantity` field) | `apps/shopper-web/src/app/features/products/product.service.ts` |
| 5.3 | Add auth token interceptor to Angular (currently web has no auth at all for tenant endpoints) | `apps/shopper-web/src/app/core/http/auth.interceptor.ts` (new) |
| 5.4 | Align mobile `ApiClient` endpoints: `/v1/auth/login` → `/v1/tenant/auth/login`; remove `refresh_token`/`expires_at` expectations; align `Product` fields | `shopper-mobile/lib/data/sources/remote/api_client.dart` |
| 5.5 | Remove `Product.brand`, `Product.color`, `Product.size`, `Product.images`, `Product.variants` from mobile entity (API doesn't serve these) | `shopper-mobile/lib/domain/entities/product.dart` |

**Tests:**
- New: `apps/shopper-web/src/app/features/products/product.service.spec.ts`
- Updated: `shopper-mobile/test/api_client_test.dart` (new)

---

### Phase 6: Web Frontend Feature Modules & Tests (2-3 days)

**What changes:**

| Step | Change | Files |
|------|--------|-------|
| 6.1 | Add route guards (auth guard) for `/products` and `/admin` routes | `apps/shopper-web/src/app/core/guards/auth.guard.ts` (new) |
| 6.2 | Add lazy loading for `admin` and `products` feature routes | `apps/shopper-web/src/app/app.routes.ts` |
| 6.3 | Resolve `ThemeService` vs `tenant-bootstrap.ts` conflict (both set `data-theme` on `<html>`) | `theme.service.ts`, `tenant-bootstrap.ts` |
| 6.4 | Add Karma/Jest unit tests for `ProductsPageComponent`, `AdminTenantsComponent`, `LocaleService` | 3 new `.spec.ts` files |
| 6.5 | Update CI to run `ng test --watch=false` | `.github/workflows/ci.yml` |

---

### Phase 7: Mobile Cleanup & Test Coverage (2-3 days)

**What changes:**

| Step | Change | Files |
|------|--------|-------|
| 7.1 | Implement the TODO: language switching in `SettingsScreen` | `shopper-mobile/lib/navigation/app_router.dart:205` |
| 7.2 | Add `SyncOrdersUseCase` to DI registration (referenced in `OrdersBloc` but not registered in `injection.dart`) | `shopper-mobile/lib/core/di/injection.dart` |
| 7.3 | Create missing repository implementations: `ProductRepository`, `CartRepository`, `SettingsRepository`, `OrderRepository` (only `auth_repository.dart` and `order_repository_impl.dart` exist) | `shopper-mobile/lib/data/repositories/` |
| 7.4 | Add widget tests for `ProductsScreen`, `CartScreen`, `CheckoutScreen` | `shopper-mobile/test/` |
| 7.5 | Add BLoC tests for all 5 blocs | `shopper-mobile/test/bloc/` |
| 7.6 | Configure Flutter CI in GitHub Actions | `.github/workflows/ci.yml` |

---

## 4. Test Strategy

### 4.1 Unit Tests

| Module | Test File | What to Test |
|--------|-----------|-------------|
| `utils/codes.py` | `tests/unit/test_codes.py` (exists) | Barcode/QR generation edge cases |
| `core/host_tenant.py` | `tests/unit/test_host_tenant.py` (exists) | Subdomain parsing |
| `core/security.py` | `tests/unit/test_security.py` (new) | Token creation, verification, expiry |
| `utils/decimal_helpers.py` | `tests/unit/test_decimal_helpers.py` (new) | Row → dict conversion with Decimal coercion |
| `services/receipt_renderer.py` | `tests/unit/test_receipt_renderer.py` (new) | Bilingual receipt output correctness |
| `services/pdf_renderer.py` | `tests/unit/test_pdf_renderer.py` (new) | PDF generation returns valid bytes |
| `services/pos_service.py` | `tests/unit/test_pos_service.py` (new) | Validation, error accumulation, stock math |
| `schemas/pos.py` | `tests/unit/test_pos_schemas.py` (new) | Pydantic validation for offline punch payloads |
| `redis_client.py` | `tests/unit/test_redis_client.py` (exists) | Idempotency key building |

### 4.2 Integration Tests

| Test File | Coverage |
|-----------|----------|
| `tests/integration/test_rls_isolation.py` (exists) | Tenant A can't see tenant B data |
| `tests/integration/test_pos_e2e.py` (exists) | Full POS flow: product → order → stock → invoice → sync |
| `tests/integration/test_payment_ipn.py` (new) | IPN processing with Redis idempotency |
| `tests/integration/test_invoice_lifecycle.py` (new) | Create invoice → partial pay → full pay → status transitions |

### 4.3 Frontend Tests

| App | Test File | Coverage |
|-----|-----------|----------|
| Web | `products-page.component.spec.ts` (new) | Product list rendering, create form, deactivate |
| Web | `admin-tenants.component.spec.ts` (new) | Key save/clear, tenant list, status change |
| Web | `locale.service.spec.ts` (new) | Language switching, formatting |
| Web | `theme.service.spec.ts` (exists) | Theme toggle |

### 4.4 Mobile Tests

| Test File | Coverage |
|-----------|----------|
| `test/bloc/auth_bloc_test.dart` (new) | Login/logout state transitions |
| `test/bloc/cart_bloc_test.dart` (new) | Add/remove/clear cart |
| `test/bloc/orders_bloc_test.dart` (new) | Create order, sync |
| `test/widget/products_screen_test.dart` (new) | Product list widget |
| `test/api_client_test.dart` (new) | Mock HTTP responses, error handling |

### 4.5 Mocking & Fixtures

- **API tests:** Use `TESTING=1` env var (existing). For integration tests needing a DB, use `testcontainers` with Postgres.
- **Web tests:** Use Angular `HttpClientTestingModule` for service tests; `ComponentFixture` for component tests.
- **Mobile tests:** Use `mocktail` for repository mocks in BLoC tests; `nock` patterns for `ApiClient` tests.

---

## 5. TODO & Defect Handling

### 5.1 Extracted TODOs

| # | Location | TODO Text | Priority | Phase |
|---|----------|-----------|----------|-------|
| T1 | `shopper-mobile/lib/navigation/app_router.dart:205` | `// TODO: Implement language switching` | **LOW** | Phase 7 |
| T2 | `deps.py:15` | `# IMPORTANT: These must match auth_router.py. In production, use shared config.` | **CRITICAL** | Phase 0 |
| T3 | `auth_router.py:13` | `# In production these should come from environment variables` | **CRITICAL** | Phase 0 |
| T4 | `api_client.dart:18` | `static const String baseUrl = '...'; // Replace with actual API URL` | **HIGH** | Phase 4 |
| T5 | `admin_router.py:50` | `# Placeholder: create DB, run schema init, update tenant record` | **MEDIUM** | Not addressed (requires infra work) |
| T6 | `migration_service.py:36` | `# This is a naive implementation; in production, use COPY or batch inserts` | **MEDIUM** | Phase 3 (note in service) |

### 5.2 Discrepancy: Two Task Files

| File | Claim | Reality |
|------|-------|---------|
| `tasks.txt` (root) | Everything DONE | Appears to be aspirational/future-state |
| `docs/tasks.txt` | Most things TODO | Appears to be the honest status |

**Action:** Delete `tasks.txt` (root) or rename to `ROADMAP.md`. Promote `docs/tasks.txt` as the authoritative `TASKS.md` at repo root. Map each TODO to a GitHub Issue in Phase 0.

---

## 6. Dependency-Impact Matrix

| Module / Feature | Current Problem | Proposed Change | Impacted Files/Tests | Phase | Risk |
|---|---|---|---|---|---|
| JWT Secret | Hardcoded duplicate in 2 files | Move to `Settings.jwt_secret_key` | `config.py`, `deps.py`, `auth_router.py`, `test_api.py` | 0 | Low |
| `tenant.py` imports | Relative imports in flat module | Fix to absolute imports | `tenant.py` | 0 | None |
| Dead mobile shell | `apps/shopper-mobile/` unused | Delete directory | `apps/shopper-mobile/` | 0 | None |
| Settings secrets leak | Payment credentials in response | Split `TenantSettingsOut` / `TenantSettingsInternalOut` | `schemas.py`, `settings_router.py`, `payments_core.py`, `test_api.py` | 0 | Medium |
| API package structure | Flat files, no hierarchy | Move to `core/`, `schemas/`, `routers/`, `services/`, `utils/` | Every `.py` file + `Dockerfile` + CI | 1 | Medium |
| Tenant boilerplate | 8-line copy-paste in every router | `TenantCtxDep` dependency | 9 routers, `core/tenant_context.py` | 2 | Low |
| Business logic in routers | Cannot unit-test logic | Extract to `services/` | 6 routers → 6 services + 6 test files | 3 | Low |
| POS unvalidated input | `list[dict[str, Any]]` | Pydantic schemas | `pos_router.py`, `schemas/pos.py` (new), `test_pos_e2e.py` | 4 | Low |
| `DEDICATED_POOLS` race | Global dict, no lock | Add `asyncio.Lock` | `core/db.py` | 4 | Low |
| Mobile base URL | Hardcoded | Configurable from build/env | `api_client.dart` | 4 | Low |
| API ↔ Frontend contract | Mismatched types and endpoints | Generate OpenAPI, align clients | `api_client.dart`, `product.service.ts`, OpenAPI doc | 5 | Medium |
| Web auth | No auth interceptor for tenant endpoints | Add `auth.interceptor.ts` | `app.config.ts`, new interceptor | 5 | Low |
| Theme conflict (web) | Two systems both set `data-theme` | Merge into single `ThemeService` | `theme.service.ts`, `tenant-bootstrap.ts` | 6 | Low |
| Web test coverage | Only 2 spec files | Add component + service tests | 3+ new `.spec.ts` files, CI config | 6 | Low |
| Mobile DI gaps | `SyncOrdersUseCase` not registered; repositories missing | Complete registrations | `injection.dart`, 4 repository files | 7 | Medium |
| Mobile BLoC path | Wrong import depth in `orders_bloc.dart` | Fix path | `orders_bloc.dart` | 0 | None |

---

## Self-Review Checklist

- **Missing dependent files:** The `apps/shopper-web/src/environments/environment.ts` and `environment.prod.ts` need `apiBaseUrl` verified after any API path changes — confirmed these are unaffected since API route paths don't change.
- **Missing tests:** Added test entries for every new service, every refactored router, every new schema. Mobile BLoC tests were missing entirely — added in Phase 7.
- **Hidden coupling:** `payments_core.py` → `tenant.py` → `db.py` → `config.py` chain is deep. Phase 1 restructure preserves this chain within `core/`, making it explicit rather than hidden.
- **Incomplete migration steps:** Phase 1 (package restructure) is the riskiest — specified that `schemas/__init__.py` must re-export all models for backwards compatibility during transition.
- **Plugin boundary breaking consumers:** The `GATEWAY_REGISTRY` pattern preserves the existing `get_gateway()` call signature. No consumer code changes required when adding a new gateway — just register it.
- **Docker / CI:** `Dockerfile` CMD of `uvicorn main:app` continues to work because `main.py` stays at package root. CI `pytest` path updated in Phase 1.
- **`docs/tasks.txt` vs `tasks.txt`:** Contradictory status resolved in Phase 0 by deleting the aspirational version and promoting the honest one.
