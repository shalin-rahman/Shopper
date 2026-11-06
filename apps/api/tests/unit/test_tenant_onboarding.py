from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from core.tenant_context import TRANSACTING_TENANT_STATUSES, resolve_tenant_id
from routers.registration import RegisterTenantBody, register_tenant

TENANT_ID = UUID("22222222-2222-4222-8222-222222222222")


class FakeConn:
    def __init__(self, row=None):
        self.row = row
        self.calls = []

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return self.row

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        return TENANT_ID

    async def execute(self, sql, *args):
        self.calls.append((sql, args))

    @asynccontextmanager
    async def transaction(self):
        yield


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _request(migrate_pool):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(migrate_pool=migrate_pool)))


def _body():
    return RegisterTenantBody(
        subdomain="acme",
        company_name_en="Acme",
        company_name_bn="অ্যাকমি",
        admin_username="owner",
        admin_password="a-long-password",
    )


async def test_resolve_tenant_id_accepts_transacting_statuses():
    conn = FakeConn(row={"id": TENANT_ID, "dedicated_database_name": None})
    result = await resolve_tenant_id(FakePool(conn), "acme")

    sql, args = conn.calls[0]
    assert "ANY($2" in sql
    assert args == ("acme", ["active", "trialing", "past_due"])
    assert result["id"] == TENANT_ID


def test_transacting_statuses_exclude_blocked_states():
    for status in ("pending", "suspended", "canceled", "deleted"):
        assert status not in TRANSACTING_TENANT_STATUSES


async def test_resolve_tenant_id_unknown_raises_404():
    with pytest.raises(HTTPException) as exc:
        await resolve_tenant_id(FakePool(FakeConn(row=None)), "nope")
    assert exc.value.status_code == 404


async def test_register_without_migrate_pool_returns_503():
    with pytest.raises(HTTPException) as exc:
        await register_tenant(_request(None), _body())
    assert exc.value.status_code == 503


async def test_register_uses_migrate_pool():
    conn = FakeConn()
    result = await register_tenant(_request(FakePool(conn)), _body())

    assert result["status"] == "created"
    assert result["tenant_id"] == str(TENANT_ID)
    assert any("tenant_data.staff" in sql for sql, _ in conn.calls)
    assert any("provision_system_accounts" in sql for sql, _ in conn.calls)


async def test_register_creates_the_main_branch():
    # Stock requests with no branch header use the main branch, so every tenant needs one.
    conn = FakeConn()
    await register_tenant(_request(FakePool(conn)), _body())

    (sql, args), = [(s, a) for s, a in conn.calls if "INSERT INTO tenant_data.branches" in s]
    assert "is_main" in sql
    assert args[0] == TENANT_ID
