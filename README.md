# Shopper Multi-Tenant ERP Platform

A comprehensive SaaS ERP platform for Bangladesh with bilingual support (English/Bangla), multi-tenancy via Row-Level Security (RLS), and integrated payment gateways.

## Architecture

- **Backend**: FastAPI (Python) with PostgreSQL, AsyncPG, Pydantic Settings
- **Frontend**: Angular 17 (Web) + Flutter (Mobile POS)
- **Reverse Proxy**: OpenResty with Lua scripting and auto-SSL
- **Database**: PostgreSQL with RLS for tenant isolation (`platform` + `tenant_data`)
- **Payments**: SSLCommerz (IPN + stubs for initiate); bKash / Nagad / Rocket planned
- **Deployment**: Docker Compose with CI (pytest, `ng build`, compose validation)

## Features

- Multi-tenant ERP (products, customers, stock transactions, ledger entries)
- Storefront JSON catalog (`GET /v1/storefront/products`) and inventory aging report (`GET /v1/tenant/reports/inventory-aging`)
- Bilingual UI (en-IN-style grouping, BDT currency)
- Payment records + **IPN webhook** with tenant query parameter (`?tenant=subdomain`)
- Reporting / storefront routers (some endpoints still placeholders — see `tasks.txt`)
- **Angular** platform admin: `/admin/tenants` (session-stored admin key)
- RLS + **audit_log** with DB triggers on key financial/inventory tables

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repo>
   cd Shopper
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Run with Docker Compose**:
   ```bash
   docker compose up --build
   ```

3. **Access (typical dev)**:
   - API: http://localhost:8000 (`GET /health`)
   - Web (direct): build `web` image or use `ng serve` for local dev
   - OpenResty: http://localhost:80 → HTTPS on :443 when TLS configured
   - **Admin API**: `GET http://localhost:8000/v1/admin/tenants` with header `X-Shopper-Admin-Key` (requires `SHOPPER_ADMIN_API_KEY` + `MIGRATE_DATABASE_URL`)
   - **Admin UI**: http://localhost:4200/admin/tenants when using `ng serve` (paste admin key in the page; stored in session storage only)

## Development

| Area | Command |
|------|---------|
| API unit tests | `cd apps/api && pip install -r requirements.txt && python -m pytest` (`python-multipart` is required for form-encoded payment IPN) |
| API integration (RLS) | Set `INTEGRATION_TEST=1` and a migrate-capable DSN; see `apps/api/tests/test_integration_rls.py` |
| Web build | `cd apps/shopper-web && npm ci && npm run build` |
| Web dev server | `cd apps/shopper-web && npm ci && ng serve` (uses `proxy.conf.json` + `X-Shopper-Tenant`) |
| Mobile | `cd apps/shopper-mobile && flutter pub get && flutter run` |

## After you change code

Keep the repo consistent (see `.cursor/rules/post-change-workflow.mdc`):

1. **Tests** — extend pytest / Angular specs; run pytest and `ng build` where relevant.
2. **Docs** — update `docs/DEPLOY.md`, `docs/ARCHITECTURE_AND_SECURITY_REVIEW.md`, and this README when behavior, env vars, or URLs change.
3. **Infra** — adjust `docker-compose.yml` / OpenResty when services or routes change.
4. **Backlog** — reflect completed work in `tasks.txt`.

## Environment Variables

See `.env.example` for DB, admin key, migrate URL, CORS, payments, Redis, and TLS.

## Security

- Row-Level Security on tenant tables; transaction-scoped `app.tenant_id`
- Optional **Redis** (`REDIS_URL`) for payment IPN replay suppression (24h TTL by default)
- Admin API: shared secret header (rotate in production; use TLS only)
- HTTPS with Let's Encrypt (OpenResty); rate limiting on `/api/`
- Payment IPN: register URLs with explicit `?tenant=`; configure `SSLCOMMERZ_STORE_ID` to enforce `store_id` match

## License

[Your License Here]
