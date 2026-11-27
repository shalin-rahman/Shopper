# Shopper Repository

This repository is a multi-tenant ERP/POS platform in active implementation. It is not a single completed production release. The authoritative business specification is maintained in [docs/ShopperRequirements.txt](docs/ShopperRequirements.txt).

## What the repository currently contains

- FastAPI backend under [apps/api](apps/api)
- Angular frontend under [apps/shopper-web](apps/shopper-web)
- Flutter mobile prototype under [shopper-mobile](shopper-mobile)
- PostgreSQL and migration assets under [database](database)
- Supporting architecture, refactor, and status documents under [docs](docs)

## Current repo status

The codebase includes substantial ERP domain logic, tenant-aware routing, and initial POS flows, but the project still contains incomplete or unverified areas. Several plan and status documents describe a future state that is not yet fully reflected in code or tests.

This repo is best understood as an in-progress implementation with a documented target architecture, rather than a production-ready deployment.

## Primary sources of truth

- Business and functional requirements: [docs/ShopperRequirements.txt](docs/ShopperRequirements.txt)
- Current specification, plan, and remediation tasks: [.specify/specs/shopper-platform](.specify/specs/shopper-platform)
- Historical status/review documents may contain superseded claims; use the current requirements and verification evidence.

## Immediate evidence from the codebase

- Tenant-aware routing is implemented in [apps/api/main.py](apps/api/main.py) and [apps/api/core/tenant_context.py](apps/api/core/tenant_context.py).
- POS sync and offline punch flows are implemented in [apps/api/routers/pos.py](apps/api/routers/pos.py).
- The current task list tracks unresolved items such as auth guards, OpenAPI alignment, and mobile DI gaps in [.specify/specs/shopper-platform/tasks.md](.specify/specs/shopper-platform/tasks.md).

## Verification status

On 2026-10-24 the API suite ran with 305 passed and 19 skipped (`python -m pytest -q` in apps/api). Migrations 01 to 031 were applied on a local PostgreSQL 18.2 scratch database, and a refund and RLS smoke test passed as the shopper_app role. On 2026-11-06 the API suite ran with 318 passed and 19 skipped, and the DB-backed tests in apps/api/tests/integration ran against the scratch database as an app-role login: 11 passed, 1 skipped (the POS end-to-end test needs seeded demo data). docs/DEPLOY.md lists the settings they need; without them they skip. The full Flutter test suite passes, and `flutter analyze` reports no issues.

On 2026-11-13 the API suite was rerun (318 passed, 19 skipped) and `ng build` passed. All work up to then is committed on dev2.

On 2026-11-27, after master plan sessions A1 to A4, B1 to B7, C1, C2 and D1 to D3 (not yet committed):
- API unit: 369 passed, 35 skipped.
- API integration on the scratch DB: 28 passed, 0 skipped. These include the POS end-to-end test, which now runs.
- Migrations 032, 033 and 035 are applied on the scratch DB.
- Web (2026-11-22, no web change since): 97 unit tests passed, `ng build` passed, Playwright e2e 37 passed.
- Mobile was not rerun. Sessions E1 to E4 still have to make it work with the API.

Remaining work, in order, with tests and acceptance criteria: [master plan](docs/superpowers/plans/2026-11-13-master-plan.md). Agents start with [AGENTS.md](AGENTS.md).

## Recommended interpretation

Treat the program as a refactor-and-hardening project in progress, with the specification in [docs/ShopperRequirements.txt](docs/ShopperRequirements.txt) describing the intended business behavior while implementation status remains partially complete.
