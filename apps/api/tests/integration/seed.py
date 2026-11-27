"""Seed and drop a throwaway tenant for API flow tests on the scratch database."""

from __future__ import annotations

import uuid

import asyncpg

from routers.auth import pwd_context

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password-e2e"


async def seed_demo(migrate_dsn: str) -> dict:
    """Create an active tenant with settings, a main branch and an admin user."""
    subdomain = f"e2e{uuid.uuid4().hex[:6]}"
    conn = await asyncpg.connect(migrate_dsn)
    try:
        async with conn.transaction():
            tenant_id = await conn.fetchval(
                """
                INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
                VALUES ($1, $2, $2, 'active') RETURNING id
                """,
                subdomain,
                f"E2E {subdomain}",
            )
            await conn.execute(
                "INSERT INTO platform.tenant_settings (tenant_id) VALUES ($1)", tenant_id
            )
            branch_id = await conn.fetchval(
                """
                INSERT INTO tenant_data.branches (tenant_id, name, code, is_main)
                VALUES ($1, 'Main', 'MAIN', true) RETURNING id
                """,
                tenant_id,
            )
            staff_id = await conn.fetchval(
                """
                INSERT INTO tenant_data.staff (tenant_id, username, password_hash, full_name, role, branch_id)
                VALUES ($1, $2, $3, 'E2E Admin', 'admin', $4) RETURNING id
                """,
                tenant_id,
                ADMIN_USERNAME,
                pwd_context.hash(ADMIN_PASSWORD),
                branch_id,
            )
    finally:
        await conn.close()
    return {
        "tenant_id": tenant_id,
        "subdomain": subdomain,
        "branch_id": branch_id,
        "staff_id": staff_id,
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    }


async def _child_first_tables(conn: asyncpg.Connection) -> list[str]:
    tables = [
        r["table_name"]
        for r in await conn.fetch(
            """
            SELECT table_name FROM information_schema.columns
             WHERE table_schema = 'tenant_data' AND column_name = 'tenant_id'
               AND table_name <> 'audit_log'
             ORDER BY table_name
            """
        )
    ]
    edges = await conn.fetch(
        """
        SELECT DISTINCT c.relname AS child, p.relname AS parent
          FROM pg_constraint con
          JOIN pg_class c ON c.oid = con.conrelid
          JOIN pg_class p ON p.oid = con.confrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_namespace pn ON pn.oid = p.relnamespace
         WHERE con.contype = 'f' AND n.nspname = 'tenant_data' AND pn.nspname = 'tenant_data'
           AND c.oid <> p.oid
        """
    )
    children: dict[str, set[str]] = {t: set() for t in tables}
    for e in edges:
        if e["parent"] in children and e["child"] in children:
            children[e["parent"]].add(e["child"])
    # A table is deleted once every table that points at it is already gone.
    ordered: list[str] = []
    remaining = set(tables)
    while remaining:
        ready = sorted(t for t in remaining if not (children[t] & remaining))
        if not ready:
            raise RuntimeError(f"FK cycle among {sorted(remaining)}")
        ordered.extend(ready)
        remaining -= set(ready)
    return ordered


async def drop_tenant(migrate_dsn: str, tenant_id: uuid.UUID) -> None:
    """Delete the tenant's rows, children before parents, audit_log last, then the tenant."""
    conn = await asyncpg.connect(migrate_dsn)
    try:
        async with conn.transaction():
            for table in await _child_first_tables(conn):
                await conn.execute(f"DELETE FROM tenant_data.{table} WHERE tenant_id = $1", tenant_id)
            # Deleting audited rows writes audit_log rows, so it goes after them.
            await conn.execute("DELETE FROM tenant_data.audit_log WHERE tenant_id = $1", tenant_id)
            for table in ("billing_transactions", "subscriptions", "tenant_settings"):
                await conn.execute(f"DELETE FROM platform.{table} WHERE tenant_id = $1", tenant_id)
            await conn.execute("DELETE FROM platform.tenants WHERE id = $1", tenant_id)
    finally:
        await conn.close()
