#!/bin/bash
# Applies database/migrations on a fresh volume and records each file, so a
# later run of database/run_migrations.py skips them.
# The postgres entrypoint may source this file instead of running it, so it
# must not call exit: that would skip the init scripts after it.
set -e

if [ -d /migrations ]; then
    PSQL="psql -v ON_ERROR_STOP=1 --username $POSTGRES_USER --dbname $POSTGRES_DB"

    $PSQL -c "CREATE TABLE IF NOT EXISTS platform.schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );"

    for path in $(ls /migrations/[0-9]*.sql 2>/dev/null | sort); do
        version=$(basename "$path")
        applied=$($PSQL -tAc "SELECT 1 FROM platform.schema_migrations WHERE version = '$version'")
        if [ "$applied" = "1" ]; then
            continue
        fi
        echo "02_apply_migrations: apply $version"
        $PSQL -f "$path"
        $PSQL -c "INSERT INTO platform.schema_migrations (version) VALUES ('$version')"
    done
else
    echo "02_apply_migrations: /migrations not mounted, skipping"
fi
