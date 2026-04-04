#!/usr/bin/env python3
"""
Apply database/migrations/*.sql once each, recorded in platform.schema_migrations.

Requires `psql` on PATH and MIGRATE_DATABASE_URL (or DATABASE_URL), e.g.:
  postgresql://shopper_migrate:SECRET@localhost:5432/shopper

Docker (no local psql):
  docker compose cp database/migrations postgres:/tmp/migrations
  docker compose exec -T postgres psql -U shopper -d shopper -f /tmp/migrations/002_tenant_settings.sql
Or mount ./database/migrations and re-run 002 manually if idempotent.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

_SAFE_VER = re.compile(r"^[\w][\w.-]*\.sql$")

ROOT = Path(__file__).resolve().parent
MIGRATIONS = ROOT / "migrations"


def _dsn() -> str:
    dsn = (os.getenv("MIGRATE_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not dsn:
        print("Set MIGRATE_DATABASE_URL or DATABASE_URL (migrate-capable role).", file=sys.stderr)
        sys.exit(1)
    if "+asyncpg" in dsn:
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return dsn


def _psql(args: list[str]) -> None:
    r = subprocess.run(["psql", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr, sep="\n", file=sys.stderr)
        sys.exit(r.returncode)


def _applied(dsn: str, version: str) -> bool:
    if not _SAFE_VER.match(version):
        raise ValueError(f"unsafe migration filename: {version!r}")
    r = subprocess.run(
        [
            "psql",
            dsn,
            "-v",
            "ON_ERROR_STOP=1",
            "-tAc",
            f"SELECT 1 FROM platform.schema_migrations WHERE version = '{version}'",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout.strip() == "1"


def main() -> None:
    dsn = _dsn()
    _psql(
        [
            dsn,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            """
            CREATE TABLE IF NOT EXISTS platform.schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """,
        ]
    )
    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files:
        print("No migrations in database/migrations/")
        return
    for path in files:
        version = path.name
        if _applied(dsn, version):
            print(f"skip {version} (already applied)")
            continue
        print(f"apply {version}")
        _psql([dsn, "-v", "ON_ERROR_STOP=1", "-f", str(path)])
        _psql(
            [
                dsn,
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                f"INSERT INTO platform.schema_migrations (version) VALUES ('{version}')",
            ]
        )
    print("migrations: done")


if __name__ == "__main__":
    main()
