# Shopper Platform — Project Status Report

> **Generated:** 2026-08-26

---

## What Is This Project?

A **multi-tenant SaaS ERP/POS** for Bangladesh retail — FastAPI backend + Angular web + Flutter mobile, backed by PostgreSQL (RLS), Redis, and OpenResty.

---

## The Plan

A **7-phase refactor** defined in [`Shopper-Refactor-Plan.md`](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/docs/Shopper-Refactor-Plan.md):

| Phase | Scope | Est. Days |
|-------|-------|-----------|
| **0** | Critical bug fixes (imports, secrets, dead code, credential leak) | 1–2 |
| **1** | API → proper Python package (`core/`, `schemas/`, `routers/`, `services/`, `utils/`) | 2–3 |
| **2** | `TenantCtxDep` — eliminate 8-line tenant boilerplate in 9 routers | 1–2 |
| **3** | Service layer extraction (business logic out of routers) | 3–4 |
| **4** | POS validation + DB safety (`asyncio.Lock`, typed schemas, mobile baseUrl) | 1–2 |
| **5** | OpenAPI contract + frontend alignment (web & mobile match API shapes) | 2–3 |
| **6** | Web frontend guards, lazy-loading, theme conflict, tests | 2–3 |
| **7** | Mobile cleanup — missing repos, DI gaps, BLoC tests, language switching | 2–3 |

---

## Current State: **In Progress (Phase 3 Finished)**

- **Documentation Reorganization:** Completed. All technical files moved to `docs/` and `docs/mobile/`.
- **Phase 0 (Pre-requisites & Security Hardening):** Completed. Secrets extracted, payment secrets redacted from `settings.py`, `pgcrypto` added to audit chaining migration, and `OrdersBloc` type safety fixed.
- **Phase 1 (Package Restructuring):** Completed.
- **Phase 2 (Tenant Context & RLS Isolation):** Completed. All 9 API routers refactored to use `TenantCtxDep` dependency injection.
- **Next Up:** Phase 4 (Service Layer Extraction & Compliance Logic).

---

## Pending Items (by Priority)

### 🔴 Priority 1 — Critical (Phase 0)
| # | Task | Component |
|---|------|-----------|
| 1 | Extract duplicated JWT `SECRET_KEY` → `config.py` | API |
| 2 | Fix relative imports in `tenant.py` (`from .db` → absolute) | API |
| 3 | Add `asyncio.Lock` to `DEDICATED_POOLS` (race condition) | API |
| 4 | Fix wrong import depth in `OrdersBloc` | Mobile |

### 🟠 Priority 2 — High (Data Safety)
| # | Task | Component |
|---|------|-----------|
| 5 | Typed Pydantic schemas for `pos_router.offline_punch` | API |
| 6 | Replace `print()` with `logger.exception()` in POS exception handler | API |
| 7 | Redact payment credentials from `TenantSettingsOut` | API |
| 8 | Configurable `ApiClient.baseUrl` (currently hardcoded) | Mobile |
| 9 | Align mobile `ApiClient` endpoints + remove phantom fields | Mobile |

### 🟡 Priority 3 — Medium (Architecture)
| # | Task | Component |
|---|------|-----------|
| 10 | Restructure API into proper package | API |
| 11 | Split monolithic `schemas.py` | API |
| 12 | Create `TenantCtxDep` | API |
| 13 | Extract business logic → service layer | API |
| 14 | Resolve duplicate task files → single `TODO.md` | Repo |
| 15 | Add missing repository implementations (4 repos) | Mobile |
| 16 | Register `SyncOrdersUseCase` in DI | Mobile |

### 🟢 Priority 4 — Low (Frontend + Tests)
| # | Task | Component |
|---|------|-----------|
| 17 | Generate & commit OpenAPI spec | API |
| 18 | Angular `ProductService` matching API shape | Web |
| 19 | Auth token interceptor + route guards | Web |
| 20 | Resolve `ThemeService` vs `tenant-bootstrap.ts` conflict | Web |
| 21 | Unit tests for API services + integration tests | API |
| 22 | Angular component/service tests | Web |
| 23 | Flutter widget/BLoC tests | Mobile |
| 24 | Implement language switching in `SettingsScreen` | Mobile |
| 25 | Delete dead `apps/shopper-mobile/` directory | Repo |

---

## Key Observations

- **Zero refactor phases have been started.** The full backlog is pending.
- Multiple `analyze_errors*.txt` files (98–121 KB each) in the mobile dir suggest the Flutter app has significant compile errors.
- The README claims **"PRODUCTION READY"** — this contradicts the TODO list and refactor plan findings.
- No CI/CD pipeline appears functional for the refactor workflow.

---

## Recommended Next Steps

1. **Start Phase 0** — surgical fixes, zero risk, immediate safety improvement.
2. **Verify Flutter compiles** — the error logs are concerning; may need triage before Phase 7 work.
3. **Decide scope** — are you tackling the full 7-phase plan, or cherry-picking specific items?
