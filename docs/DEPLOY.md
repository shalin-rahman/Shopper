# Shopper VPS deployment (summary)

## DNS

- Point `A` (and `AAAA` if IPv6) for `platform.example.com` and wildcard `*.platform.example.com` to the VPS public IP used by OpenResty.

## Compose

1. Copy `.env.example` to `.env` and set production values (`SHOPPER_*`, `LETSENCRYPT_EMAIL`, `PLATFORM_ROOT_DOMAIN`, `SHOPPER_ADMIN_API_KEY`, `SHOPPER_MIGRATE_DATABASE_URL`, payment gateway vars).
2. First boot: Postgres runs `database/init` (including `02_apply_migrations.sh`, which applies every `database/migrations/*.sql` in lexical order). The `migrations` folder is mounted at `/migrations`.
3. Run: `docker compose up -d --build`.
4. **Existing databases** (created before a new `migrations/*.sql` file): run `python database/run_migrations.py` with `MIGRATE_DATABASE_URL` set and `psql` on `PATH`, or apply the SQL manually once (files are idempotent where possible).

### Notable migrations (non-exhaustive)

| File | Purpose |
|------|---------|
| `002_tenant_settings.sql` | Storefront / console bootstrap (`theme_id`, BIN, `module_access`, …) |
| `003_payments.sql` | `tenant_data.payments` + RLS |
| `004_audit_log.sql` | Append-only `tenant_data.audit_log` |
| `005_stock.sql` | `tenant_data.stock_transactions` |
| `006_ledger.sql` | `tenant_data.ledger_entries` |
| `007_billing.sql` | Subscription/billing tables |
| `008_audit_triggers.sql` | Triggers: products, stock, payments, ledger → `audit_log` |
| `009_vat_sales_register_lines.sql` | Mushak-oriented line facts (if not already from init) |

## TLS

- OpenResty uses **lua-resty-auto-ssl**; set `LETSENCRYPT_EMAIL` and `PLATFORM_ROOT_DOMAIN`. Use `LETSENCRYPT_STAGING=1` while testing.
- Ensure port **80** is reachable from the internet for HTTP-01 challenges.

## Public / tenant API highlights

- **Storefront catalog:** `GET /v1/storefront/products?limit=&offset=&q=` — tenant from `X-Shopper-Tenant` (dev) or subdomain on `Host` when `PLATFORM_ROOT_DOMAIN` is set.
- **Inventory aging:** `GET /v1/tenant/reports/inventory-aging?as_of=YYYY-MM-DD` — requires tenant context like other `/v1/tenant/*` routes.

## Redis

- Set `REDIS_URL` (e.g. `redis://redis:6379/0` in Compose). Leave **empty** to disable Redis entirely.
- **IPN replay:** successful payment callbacks record a key `shopper:ipn:v1:{tenant}:{gateway}:{val_id|tran_id}` with TTL `REDIS_IPN_TTL_SECONDS` (default 86400). Replays return `{ "idempotent": true, "source": "redis" }` without hitting Postgres again.
- If Redis is unreachable at startup, the API logs a warning and runs without Redis (same as disabled).

## Payment IPN (webhooks)

Gateways cannot send `X-Shopper-Tenant`. Register the callback with a **tenant subdomain query parameter**:

- Example: `https://your-api-host/v1/tenant/payments/ipn/sslcommerz?tenant=demo`
- Body: **form-encoded** (SSLCommerz) or **JSON**.
- When `SSLCOMMERZ_STORE_ID` is set, the IPN payload’s `store_id` must match; `status=VALID` maps to payment **completed** (see `apps/api/payments_router.py`).
- Full **remote validation** of SSLCommerz `val_id` against their API is still required for production hardening (see `tasks.txt`).

## Super Admin

- **HTTP API:** `GET/PATCH /v1/admin/...` with header `X-Shopper-Admin-Key` (value = `SHOPPER_ADMIN_API_KEY`). Requires `MIGRATE_DATABASE_URL` on the API process.
- **Angular:** route `/admin/tenants` — operator pastes the admin key into **session storage** only (not baked into the build). Use HTTPS in production.

## Backups

- Schedule `pg_dump` (or volume snapshots) for the Postgres data volume; store off-server.

## Updates

- Pull images/build, `docker compose up -d --build`, then run `python database/run_migrations.py` (as `shopper_migrate`) for any new `database/migrations/*.sql` not yet recorded in `platform.schema_migrations`.

## Verification after changes

- API: `cd apps/api && pip install -r requirements.txt && python -m pytest` (includes `python-multipart` for payment IPN form posts)
- Web: `cd apps/shopper-web && npm ci && npm run build`
- Compose: `docker compose -f docker-compose.yml config --quiet`

## Maintainer checklist

When merging behavior changes: update **tests**, **docs** (`DEPLOY`, `ARCHITECTURE_AND_SECURITY_REVIEW`, root `README` as appropriate), **`tasks.txt`**, and **compose/OpenResty** if routing or env vars change. See `.cursor/rules/post-change-workflow.mdc`.
