# Shopper Platform — Master Task List

Based on the architectural and code review (`docs/Shopper-Refactor-Plan.md`), here is the consolidated, prioritized task list to be executed. Tasks are grouped by priority (Critical/High/Medium/Low).

### Priority 1: Critical (Immediate Fixes)
- [ ] **API:** Extract duplicated JWT `SECRET_KEY` from `deps.py` and `auth_router.py` into `config.py` as `Settings.jwt_secret_key`. (Phase 0)
- [ ] **API:** Fix relative imports (`from .db`, `from .config`) in `tenant.py` to absolute imports to prevent runtime crashes. (Phase 0)
- [ ] **API:** Ensure `DEDICATED_POOLS` global dict in `db.py` uses `asyncio.Lock` to prevent race conditions during concurrent provisioning. (Phase 4)
- [ ] **Mobile:** Fix wrong import depth for `OrdersBloc` in `shopper-mobile/lib/core/bloc/orders/orders_bloc.dart`. (Phase 0)

### Priority 2: High (Data Safety & Core Stability)
- [ ] **API:** Define Pydantic schemas (`OfflinePunchOrder`, `OfflinePunchItem`) for `pos_router.offline_punch` to validate input and avoid untyped `list[dict]` arithmetic. (Phase 4)
- [ ] **API:** Fix silently swallowed exceptions in `pos_router.py:offline-punch` by replacing `print()` with `logger.exception()` and accumulating errors. (Phase 4)
- [ ] **API:** Redact payment credentials (bKash, Nagad) from `TenantSettingsOut` by splitting into `TenantSettingsInternalOut` for admin use only. (Phase 0)
- [ ] **Mobile:** Refactor `ApiClient.baseUrl` from hardcoded string to a configurable constant loaded from build config. (Phase 4)
- [ ] **Mobile:** Align `ApiClient` endpoints (e.g., `/v1/tenant/auth/login`) and remove unserved fields (like `refresh_token`, `Product.brand`, etc.). (Phase 5)

### Priority 3: Medium (Architecture & Refactoring)
- [ ] **API:** Restructure API into a proper package with `core/`, `schemas/`, `routers/`, `services/`, and `utils/` directories. (Phase 1)
- [ ] **API:** Split monolithic `schemas.py` into domain-specific files (`product.py`, `customer.py`, etc.). (Phase 1)
- [ ] **API:** Create a `TenantCtxDep` to eliminate the 8-line tenant resolution boilerplate across all 9 routers. (Phase 2)
- [ ] **API:** Extract business logic from routers into services (`product_service.py`, `invoice_service.py`, `pos_service.py`, etc.). (Phase 3)
- [ ] **Repo:** Resolve discrepancy between `tasks.txt` and `docs/tasks.txt` by establishing a single source of truth (`TODO.md`). (Phase 0)
- [ ] **Mobile:** Add missing repository implementations (`ProductRepository`, `CartRepository`, `SettingsRepository`, `OrderRepository`). (Phase 7)
- [ ] **Mobile:** Add `SyncOrdersUseCase` to DI registration in `injection.dart`. (Phase 7)

### Priority 4: Low (Frontend Alignment & Test Coverage)
- [ ] **API:** Generate OpenAPI spec (`/openapi.json`) and commit to `docs/openapi.json`. (Phase 5)
- [ ] **Web:** Create `ProductService` in Angular matching the actual API response shape. (Phase 5)
- [ ] **Web:** Implement auth token interceptor (`auth.interceptor.ts`) and route guards for protected routes. (Phase 6)
- [ ] **Web:** Resolve conflict between `ThemeService` and `tenant-bootstrap.ts` for setting `data-theme`. (Phase 6)
- [ ] **Testing:** Add unit tests for API services (`test_security.py`, `test_pos_service.py`, etc.) and integration tests (`test_payment_ipn.py`). (Phase 4)
- [ ] **Testing:** Add Angular component/service tests and Flutter widget/BLoC tests. (Phase 6 & 7)
- [ ] **Mobile:** Implement language switching in `SettingsScreen`. (Phase 7)
- [ ] **Repo:** Delete the dead mobile shell directory (`apps/shopper-mobile/`). (Phase 0)
