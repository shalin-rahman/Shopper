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
   - `PLATFORM_ROOT_DOMAIN`: the bare root domain, for example `shop.example`. The API reads the tenant from the Host: `acme.shop.example` is tenant `acme`. Do not put a scheme or path in it.
   - `STOREFRONT_PUBLIC_BASE_URL`: root URL of the tenant sites, for example `https://shop.example`. Links get the tenant in front of the host (`https://acme.shop.example`), or fill a `{subdomain}` placeholder. Use host style with no path: gateway callbacks go to `/api/...` on that host, and OpenResty serves `/api/` only at the root. Use the same root as `PLATFORM_ROOT_DOMAIN`, and make sure wildcard DNS and TLS cover it. Empty means `https://<tenant>.shopper.com`.
   - `LETSENCRYPT_EMAIL`: for automated TLS.

## Deployment Steps
1. **Build and Start**:
   ```bash
   docker compose up -d --build
   ```
2. **Apply Migrations** (01 to 031 today; 032 and 033 are planned, see the master plan. Before 032 runs on real data, run `database/checks/032_precheck.sql`; every count must be 0):
   The `run_migrations.py` script automatically applies sequential SQL files from `database/migrations/`.
   ```bash
   docker compose exec api python database/run_migrations.py
   ```

## Post-Deployment Verification
- **Health Check**: `GET /health`
- **Isolation Suite**: From apps/api, set `INTEGRATION_TEST=1`, `MIGRATE_DATABASE_URL` (migrate role, seeds and cleans up test tenants), `DATABASE_URL` (shopper_app, no BYPASSRLS) and `JWT_SECRET_KEY`, then run `python -m pytest tests/integration -q`. Run it on a staging or scratch database, not production: it creates and deletes two test tenants. Without these settings the RLS tests skip. Last run 2026-11-06 on a local scratch DB: 11 passed, 1 skipped.
- **E2E Flow**: `tests/integration/test_pos_e2e.py` always skips today: the test setup forces `TESTING=1`, and the test also needs a seeded tenant. Master plan session A4 makes it run under the same settings as the isolation suite.

## Payment & Webhook Configuration
- The IPN route is `POST /v1/tenant/payments/ipn/{gateway}?tenant=<subdomain>`. Behind OpenResty it is reached at `https://<tenant>.<root>/api/v1/tenant/payments/ipn/sslcommerz?tenant=<tenant>` (OpenResty strips `/api`).
- **Known issue (2026-11-13), fix in master plan A2:** the SSLCommerz IPN URL the API sends is built from `PLATFORM_ROOT_DOMAIN`, so it has no scheme, tenant or `/api`. The success, fail and cancel URLs point at `/checkout/success|fail|cancel` on the web app, which cannot take the gateway's POST. Do not take live SSLCommerz payments until A2 is done.
- bKash and Nagad fail closed and Rocket returns 501 until provider contracts arrive.
- Ensure `HMAC` secrets and `Store ID` credentials match your gateway dashboards.

## Backup Strategy
- Use `pg_dump` on the `shopper` database regularly.
- Ensure `database/migrations/` are version-controlled alongside your code.

---
## Before production (2026-11-13)
Required sessions from the [master plan](superpowers/plans/2026-11-13-master-plan.md): A2 (gateway URLs), A3 (money endpoint roles), C1 and C2 (tenant-qualified foreign keys), D1 and D2 (DB-backed tests), and the live checks in X4 (wildcard DNS and TLS, one SSLCommerz sandbox payment end to end, printed QR opens the right tenant). The mobile POS cannot work against this API until E1 to E4 are done.

---
**Status:** not yet production ready. Open work: [master plan](superpowers/plans/2026-11-13-master-plan.md). History and evidence: [tasks.md](../.specify/specs/shopper-platform/tasks.md).
