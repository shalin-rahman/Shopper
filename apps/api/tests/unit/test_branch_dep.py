from uuid import UUID

import pytest
from fastapi import HTTPException

from core.dependencies import current_branch

MAIN = UUID(int=10)
OTHER = UUID(int=11)
ADMIN = {"uid": str(UUID(int=0)), "role": "admin", "tid": "t"}


class Conn:
    def __init__(self, found=True):
        self.found = found
        self.sql = []

    async def fetchval(self, sql, *args):
        self.sql.append(" ".join(sql.split()))
        if "WHERE is_main" in sql:
            return MAIN
        return args[0] if self.found else None


@pytest.mark.asyncio
async def test_no_header_uses_main_branch():
    assert await current_branch(ADMIN, None).resolve(Conn()) == MAIN


@pytest.mark.asyncio
async def test_header_names_an_active_branch():
    conn = Conn()

    assert await current_branch(ADMIN, str(OTHER)).resolve(conn) == OTHER
    assert "is_active" in conn.sql[0]


def test_malformed_header_is_400():
    with pytest.raises(HTTPException) as exc:
        current_branch(ADMIN, "not-a-uuid")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_unknown_or_other_tenant_branch_is_400():
    # RLS hides another tenant's branch, so it looks the same as an unknown one.
    with pytest.raises(HTTPException) as exc:
        await current_branch(ADMIN, str(OTHER)).resolve(Conn(found=False))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_named_branch_is_share_locked():
    # A deactivation waits for this request, so stock cannot land at a branch
    # that was deactivated while the request ran.
    conn = Conn()

    await current_branch(ADMIN, str(OTHER)).resolve(conn)

    assert "FOR SHARE" in conn.sql[-1]


HOME = UUID(int=12)
STAFF = UUID(int=50)


class StaffConn(Conn):
    def __init__(self, home=HOME, exists=True):
        super().__init__()
        self.home = home
        self.exists = exists

    async def fetchrow(self, sql, *args):
        self.sql.append(" ".join(sql.split()))
        assert "FROM tenant_data.staff" in sql and args == (STAFF,)
        return {"branch_id": self.home} if self.exists else None


def _who(role):
    return {"uid": str(STAFF), "role": role, "tid": "t"}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["cashier", "accountant"])
async def test_limited_role_without_header_works_at_home(role):
    assert await current_branch(_who(role), None).resolve(StaffConn()) == HOME


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["cashier", "accountant"])
async def test_limited_role_cannot_pick_another_branch(role):
    with pytest.raises(HTTPException) as exc:
        await current_branch(_who(role), str(OTHER)).resolve(StaffConn())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_limited_role_may_name_its_own_branch():
    assert await current_branch(_who("cashier"), str(HOME)).resolve(StaffConn()) == HOME


@pytest.mark.asyncio
async def test_cashier_with_no_home_works_at_main():
    assert await current_branch(_who("cashier"), None).resolve(StaffConn(home=None)) == MAIN


@pytest.mark.asyncio
async def test_unknown_staff_is_403():
    with pytest.raises(HTTPException) as exc:
        await current_branch(_who("cashier"), None).resolve(StaffConn(exists=False))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin", "manager"])
async def test_admin_and_manager_pick_any_branch(role):
    conn = Conn()
    assert await current_branch(_who(role), str(OTHER)).resolve(conn) == OTHER
    assert not any("tenant_data.staff" in s for s in conn.sql)
