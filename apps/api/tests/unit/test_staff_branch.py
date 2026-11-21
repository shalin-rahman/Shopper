"""Staff can be given a home branch when they are created."""

from uuid import UUID

import pytest
from fastapi import HTTPException

from routers.staff import create_staff
from schemas import StaffCreate

SHOP = UUID(int=2)
ADMIN = {"uid": str(UUID(int=0)), "role": "admin", "tid": "t"}


class Conn:
    def __init__(self):
        self.inserted = None

    async def fetchval(self, sql, *args):
        assert "FROM tenant_data.branches" in sql
        return args[0] if args[0] == SHOP else None

    async def fetchrow(self, sql, *args):
        self.inserted = args
        return {"id": UUID(int=7), "username": args[1], "role": args[4], "branch_id": args[5]}


class Tx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class Ctx:
    tenant_id = UUID(int=9)

    def __init__(self, conn):
        self.conn = conn

    def transaction(self):
        return Tx(self.conn)


def _body(**extra):
    return StaffCreate(username="rina", password="pw-123456", role="cashier", **extra)


@pytest.mark.asyncio
async def test_staff_created_with_a_branch():
    conn = Conn()
    out = await create_staff(Ctx(conn), _body(branch_id=str(SHOP)), ADMIN)
    assert conn.inserted[5] == SHOP
    assert out["branch_id"] == SHOP


@pytest.mark.asyncio
async def test_staff_without_branch_stores_null():
    conn = Conn()
    await create_staff(Ctx(conn), _body(), ADMIN)
    assert conn.inserted[5] is None


@pytest.mark.asyncio
async def test_inactive_branch_is_400():
    conn = Conn()
    with pytest.raises(HTTPException) as exc:
        await create_staff(Ctx(conn), _body(branch_id=str(UUID(int=3))), ADMIN)
    assert exc.value.status_code == 400
    assert conn.inserted is None
