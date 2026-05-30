#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    ALTER ROLE shopper_app WITH PASSWORD '${SHOPPER_APP_PASSWORD}';
    ALTER ROLE shopper_migrate WITH PASSWORD '${SHOPPER_MIGRATE_PASSWORD}';
EOSQL