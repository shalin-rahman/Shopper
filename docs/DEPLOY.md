# Shopper VPS Deployment Guide (Hardened Edition)

## DNS Configuration
- Set `A`/`AAAA` records for `platform.yourdomain.com` and a wildcard `*.platform.yourdomain.com` to your VPS public IP.
- OpenResty handles automatic SSL via Let's Encrypt for all resolved subdomains.

## Environment Setup
1. Copy `.env.example` to `.env`.
2. Configure critical variables:
   - `DATABASE_URL`: Main connection pool.
   - `MIGRATE_DATABASE_URL`: Migrator role connection.
   - `REDIS_URL`: For IPN idempotency and caching.
   - `SHOPPER_ADMIN_API_KEY`: Secure key for the Admin Dashboard.
   - `JWT_SECRET_KEY`: Required. The API refuses to start with an empty or weak value.
   - `PRINTED_CHECKOUT_LINK_DAYS`: How many days the pay link in a printed invoice QR code works. Default 30, allowed 1 to 365.
   - `ALLOW_TENANT_OVERRIDE`: Keep `false` in production. When `true`, any caller can pick a tenant with the `X-Shopper-Tenant` header, and localhost or a bare IP falls back to `demo`. docker-compose defaults to `false`; `.env.example` sets `true` for local dev.
   - `LETSENCRYPT_EMAIL` & `PLATFORM_ROOT_DOMAIN`: For automated TLS.

## Deployment Steps
1. **Build and Start**:
   ```bash
   docker compose up -d --build
   ```
2. **Apply Migrations**:
   The `run_migrations.py` script automatically applies sequential SQL files from `database/migrations/`.
   ```bash
   docker compose exec api python database/run_migrations.py
   ```

## Post-Deployment Verification
- **Health Check**: `GET /health`
- **Isolation Suite**: From apps/api, set `INTEGRATION_TEST=1`, `MIGRATE_DATABASE_URL` (migrate role, seeds and cleans up test tenants), `DATABASE_URL` (shopper_app, no BYPASSRLS) and `JWT_SECRET_KEY`, then run `python -m pytest tests/integration -q`. Run it on a staging or scratch database, not production: it creates and deletes two test tenants. Without these settings the RLS tests skip. Last run 2026-11-06 on a local scratch DB: 11 passed, 1 skipped.
- **E2E Flow**: `tests/integration/test_pos_e2e.py` needs `TESTING` unset and a seeded `demo` tenant with an admin/password staff login. It skips otherwise.

## Payment & Webhook Configuration
- Register IPN callbacks with the `?tenant=subdomain` parameter.
- Example: `https://api.yourdomain.com/v1/tenant/payments/ipn/sslcommerz?tenant=demo`
- Ensure `HMAC` secrets and `Store ID` credentials match your gateway dashboards.

## Backup Strategy
- Use `pg_dump` on the `shopper` database regularly.
- Ensure `database/migrations/` are version-controlled alongside your code.

---
**Status:** not yet production ready. See the open items in [tasks.md](../.specify/specs/shopper-platform/tasks.md).
