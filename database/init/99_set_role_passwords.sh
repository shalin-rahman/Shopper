#!/usr/bin/env sh
# Runs after SQL init; passwords from env (see .env.example). Uses psql :'var' quoting.
set -eu

APP_PW="${SHOPPER_APP_PASSWORD:-shopper_app_change_me}"
MIG_PW="${SHOPPER_MIGRATE_PASSWORD:-shopper_migrate_change_me}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v "app_pw=$APP_PW" \
    -v "mig_pw=$MIG_PW" \
    -c "ALTER ROLE shopper_app PASSWORD :'app_pw'; ALTER ROLE shopper_migrate PASSWORD :'mig_pw';"
