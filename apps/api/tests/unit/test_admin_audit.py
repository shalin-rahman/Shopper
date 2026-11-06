from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from core.config import Settings
from routers.admin import TenantStatusBody, set_tenant_status

TENANT_ID = UUID("33333333-3333-4333-8333-333333333333")
ADMIN_KEY = "admin-key"


class FakeConn:
    def __init__(self, current_status):
        self.current_status = current_status
        self.calls = []
        self.in_transaction = False

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        return self.current_status

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return {"id": TENANT_ID, "status": args[1]}

    async def execute(self, sql, *args):
        assert self.in_transaction, "audit row must be written in the status-change transaction"
        self.calls.append((sql, args))

    @asynccontextmanager
    async def transaction(self):
        self.in_transaction = True
        yield
        self.in_transaction = False


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _call(conn, status="suspended"):
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(migrate_pool=FakePool(conn))))
    settings = Settings(_env_file=None, shopper_admin_api_key=ADMIN_KEY)
    return set_tenant_status(request, TENANT_ID, TenantStatusBody(status=status), settings, ADMIN_KEY)


async def test_set_tenant_status_writes_audit_row():
    conn = FakeConn(current_status="active")
    result = await _call(conn)

    assert result["status"] == "suspended"
    audit = [(sql, args) for sql, args in conn.calls if "tenant_data.audit_log" in sql]
    assert len(audit) == 1
    sql, args = audit[0]
    assert "'platform.tenants'" in sql
    assert "'platform-admin'" in sql
    assert args == (TENANT_ID, "active", "suspended")


async def test_set_tenant_status_unknown_tenant_is_404_without_audit():
    conn = FakeConn(current_status=None)
    with pytest.raises(HTTPException) as exc:
        await _call(conn)
    assert exc.value.status_code == 404
    assert not any("audit_log" in sql for sql, _ in conn.calls)
