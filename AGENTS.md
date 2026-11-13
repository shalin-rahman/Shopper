# Shopper: notes for every coding agent

Read this first. It is short on purpose. Claude, Cursor, Codex, Copilot and Gemini all use it.

## What this is
Multi-tenant ERP and POS for Bangladeshi shops. FastAPI + asyncpg + PostgreSQL RLS (`apps/api`), Angular 17 web (`apps/shopper-web`), Flutter POS (`shopper-mobile`), SQL migrations (`database/migrations`), OpenResty (`infra/openresty`). Requirements: `docs/ShopperRequirements.txt` (authoritative), traced in `.specify/specs/shopper-platform/spec.md`.

## Where the work is
- **Plan for all remaining work:** `docs/superpowers/plans/2026-11-13-master-plan.md`. Pick the first `todo` row in its Tracker whose `Needs` are done. Read only that session. It lists files, code, tests and acceptance.
- After a session: set its Tracker row to `done` with date and test counts. Do not edit README, DEPLOY, ARCHITECTURE_MAP, spec.md or tasks.md: session G3 does that once.
- `tasks.md` holds history and evidence. Older plans in `docs/superpowers/plans/2026-10-23-*` are finished. `docs/TODO.md`, `docs/AI_*`, `docs/Shopper-Refactor-Plan.md` are historical.

## Commands
- API: `cd apps/api && python -m pytest -q` (baseline 2026-11-13: 318 passed, 19 skipped).
- API integration (scratch DB `shopper_verify` only): `INTEGRATION_TEST=1`, `MIGRATE_DATABASE_URL`, `DATABASE_URL` (member of shopper_app, NOBYPASSRLS), `JWT_SECRET_KEY` (32+ chars), then `python -m pytest tests/integration -q`.
- Web: `cd apps/shopper-web && npx ng test --watch=false --browsers=ChromeHeadless && npx ng build`.
- Mobile: `cd shopper-mobile && flutter test && flutter analyze`.

## Rules that broke things before
- Never use the `shopper`, `ShoppersDB` or any Neon database. Only the scratch DB `shopper_verify`.
- Migrations: next number 032 (see the plan). One `BEGIN; ... COMMIT;`, safe to rerun, plus a static test `tests/unit/test_migration_0NN.py`.
- Lock product rows (`services.stock.lock_products`) before `lock_levels`. A tenant-row lock before an audit insert must be `FOR NO KEY UPDATE` (the audit trigger takes an advisory lock).
- asyncpg has no JSONB codec: parse JSONB text with `json.loads`, write with `json.dumps(...)` and `::jsonb`.
- The API refuses to start without a real `JWT_SECRET_KEY` (32+ chars) unless `TESTING`. bcrypt stays `<5` (passlib 1.7.4).
- Tenant comes from the Host (`<tenant>.<PLATFORM_ROOT_DOMAIN>`); `X-Shopper-Tenant` and localhost work only with `ALLOW_TENANT_OVERRIDE=true` (dev).
- Storefront and gateway links go through `apps/api/core/storefront_url.py`.
- Web: strings in both `en.json` and `bn.json`; use `--shopper-*` tokens and shared classes in `src/styles.scss`; component styles under 4 kB (build fails) and ideally 2 kB; check pages at 360 px in Bangla.
- Text files are stored LF (`.gitattributes`). Do not rewrite whole files for line endings.
- Commit only when the user asks.

## After a change
Add or update a test. If you add an env var, update `.env.example` and `docs/DEPLOY.md`. If routes change after session E4, rerun `python apps/api/scripts/export_openapi.py`.
