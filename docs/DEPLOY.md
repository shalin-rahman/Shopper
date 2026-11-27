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
2. **Apply Migrations** (01 to 033 and 035 today; 034 is kept for master plan session F2 and will be added later):
   - Before 032 runs on real data, run `database/checks/032_precheck.sql`. Every count must be 0. 032 is one transaction, so if a check fails inside it, nothing is applied.
   - 032 makes every tenant foreign key include `tenant_id`, so one shop cannot point at another shop's rows. It needs PostgreSQL 15 or newer.
   - 033 fixes stock-in. Since 013, every stock-in failed on a real database. 033 also gives each product that has stock but no cost layer one layer at its average or buy price, so its sales are no longer costed at 0.
   - 035 lets trialing and past_due shops appear in marketplace search, not only active ones.
   The `run_migrations.py` script applies each file in `database/migrations/` once, in name order, and records it in `platform.schema_migrations`. A file added later with a lower number (034) is still applied.
   ```bash
   docker compose exec api python database/run_migrations.py
   ```

## Post-Deployment Verification
- **Health Check**: `GET /health`
- **Isolation Suite**: From apps/api, set `INTEGRATION_TEST=1`, `MIGRATE_DATABASE_URL` (migrate role, seeds and cleans up test tenants), `DATABASE_URL` (shopper_app, no BYPASSRLS) and `JWT_SECRET_KEY`, then run `python -m pytest tests/integration -q`. Run it on a staging or scratch database, not production: it creates and deletes two test tenants. Without these settings the RLS tests skip. Last run 2026-11-27 on a local scratch DB: 28 passed, 0 skipped.
- **E2E and flow tests**: the same command also runs the POS end-to-end test, product, invoice, return and refund flows, cross-tenant foreign key checks, marketplace search, and tenant status checks. Each test seeds its own random tenant and deletes it afterwards.

## Payment & Webhook Configuration
- The IPN route is `POST /v1/tenant/payments/ipn/{gateway}?tenant=<subdomain>`. Behind OpenResty it is reached at `https://<tenant>.<root>/api/v1/tenant/payments/ipn/sslcommerz?tenant=<tenant>` (OpenResty strips `/api`).
- The API builds the gateway URLs from `STOREFRONT_PUBLIC_BASE_URL` (fixed 2026-11-22, master plan A2). For tenant `acme` with base `https://shop.example`:
  - IPN: `https://acme.shop.example/api/v1/tenant/payments/ipn/sslcommerz?tenant=acme`
  - Success, fail, cancel: `https://acme.shop.example/api/v1/storefront/checkout/return/success|fail|cancel`. This route accepts the gateway's POST and sends the browser on to `/checkout/result?status=...` on the web app.
  A base with a path (`https://shop.example/stores`) breaks these URLs, because OpenResty serves `/api/` only at the root. Before taking live payments, run one sandbox payment end to end (master plan X4).
- bKash and Nagad fail closed and Rocket returns 501 until provider contracts arrive.
- Ensure `HMAC` secrets and `Store ID` credentials match your gateway dashboards.

## Backup Strategy
- Use `pg_dump` on the `shopper` database regularly.
- Ensure `database/migrations/` are version-controlled alongside your code.

---
## Before production (updated 2026-11-27)
Done: A2 (gateway URLs), A3 (money endpoint roles), C1 and C2 (tenant-qualified foreign keys), D1 to D3 (DB-backed tests, marketplace status). Still needed from the [master plan](superpowers/plans/2026-11-13-master-plan.md): the live checks in X4 (wildcard DNS and TLS, one SSLCommerz sandbox payment end to end, printed QR opens the right tenant). The mobile POS cannot work against this API until E1 to E4 are done.

---
**Status:** not yet production ready. Open work: [master plan](superpowers/plans/2026-11-13-master-plan.md). History and evidence: [tasks.md](../.specify/specs/shopper-platform/tasks.md).
