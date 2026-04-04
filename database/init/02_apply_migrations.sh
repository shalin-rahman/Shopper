#!/usr/bin/env sh
# Apply versioned SQL from /migrations (mounted in docker-compose). Runs after 01_schema_rls.sql on first boot.
set -eu
if [ ! -d /migrations ]; then
  echo "shopper: /migrations not mounted; skipping incremental migrations."
  exit 0
fi
for f in /migrations/*.sql; do
  [ -f "$f" ] || continue
  echo "shopper init: applying $(basename "$f")"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$f"
done
