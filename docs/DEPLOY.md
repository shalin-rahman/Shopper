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
- **Isolation Suite**: Run `pytest apps/api/tests/test_isolation.py` to verify tenant safety.
- **E2E Flow**: Run `pytest apps/api/tests/test_pos_e2e.py` to verify the full transaction lifecycle.

## Payment & Webhook Configuration
- Register IPN callbacks with the `?tenant=subdomain` parameter.
- Example: `https://api.yourdomain.com/v1/tenant/payments/ipn/sslcommerz?tenant=demo`
- Ensure `HMAC` secrets and `Store ID` credentials match your gateway dashboards.

## Backup Strategy
- Use `pg_dump` on the `shopper` database regularly.
- Ensure `database/migrations/` are version-controlled alongside your code.

---
**Status:** **[PRODUCTION DEPLOYABLE]**
