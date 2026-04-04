# Shopper VPS deployment (summary)

## DNS

- Point `A` (and `AAAA` if IPv6) for `platform.example.com` and wildcard `*.platform.example.com` to the VPS public IP used by OpenResty.

## Compose

1. Copy `.env.example` to `.env` and set production values (`SHOPPER_*`, `LETSENCRYPT_EMAIL`, `PLATFORM_ROOT_DOMAIN`, `SHOPPER_ADMIN_API_KEY`, `SHOPPER_MIGRATE_DATABASE_URL`).
2. First boot: Postgres runs `database/init` (including `02_apply_migrations.sh`, which applies every `database/migrations/*.sql`). The `migrations` folder is mounted at `/migrations`.
3. Run: `docker compose up -d --build`.
4. **Existing databases** (created before a new `migrations/*.sql` file): run `python database/run_migrations.py` with `MIGRATE_DATABASE_URL` set and `psql` on `PATH`, or apply the SQL manually once (files are idempotent where possible).

## TLS

- OpenResty uses **lua-resty-auto-ssl**; set `LETSENCRYPT_EMAIL` and `PLATFORM_ROOT_DOMAIN`. Use `LETSENCRYPT_STAGING=1` while testing.
- Ensure port **80** is reachable from the internet for HTTP-01 challenges.

## Backups

- Schedule `pg_dump` (or volume snapshots) for the Postgres data volume; store off-server.

## Updates

- Pull images/build, `docker compose up -d --build`, then run `python database/run_migrations.py` (as `shopper_migrate`) for any new `database/migrations/*.sql` not yet recorded in `platform.schema_migrations`.
