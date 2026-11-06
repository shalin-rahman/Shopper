"""Branch list, create and edit."""

from datetime import datetime, timezone
from uuid import UUID

import asyncpg
import pytest
from fastapi import HTTPException

from routers.branches import BranchCreate, BranchUpdate, create_branch, list_branches, update_branch

TENANT = UUID(int=9)
MAIN = UUID(int=0xB1)
SHOP = UUID(int=0xB2)


def _row(id, name, code, is_main=False, is_active=True):
    now = datetime.now(timezone.utc)
    return {
        "id": id, "tenant_id": TENANT, "name": name, "code": code, "is_main": is_main,
        "is_active": is_active, "created_at": now, "updated_at": now,
    }


class Conn:
    def __init__(self, held=0):
        self.rows = {MAIN: _row(MAIN, "Main branch", "MAIN", is_main=True), SHOP: _row(SHOP, "Shop", "SHOP")}
        self.inserted = []
        self.held = held

    async def fetchval(self, sql, *args):
        assert "FROM tenant_data.stock_levels" in sql
        return self.held > 0

    async def fetch(self, sql, *args):
        assert "FROM tenant_data.branches" in sql
        return list(self.rows.values())

    async def fetchrow(self, sql, *args):
        if "INSERT INTO tenant_data.branches" in sql:
            tenant_id, name, code = args
            if any(r["code"] == code for r in self.rows.values()):
                raise asyncpg.exceptions.UniqueViolationError("duplicate code")
            self.inserted.append(args)
            return _row(UUID(int=0xB3), name, code)
        if "SELECT" in sql and "FROM tenant_data.branches" in sql:
            return self.rows.get(args[0])
        if "UPDATE tenant_data.branches" in sql:
            branch_id = args[0]
            row = dict(self.rows[branch_id])
            row["name"] = args[1] if args[1] is not None else row["name"]
            row["is_active"] = args[2] if args[2] is not None else row["is_active"]
            self.rows[branch_id] = row
            return row
        raise AssertionError(sql)


class Tx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class Ctx:
    tenant_id = TENANT

    def __init__(self, conn):
        self.conn = conn

    def transaction(self):
        return Tx(self.conn)


@pytest.mark.asyncio
async def test_list_returns_every_branch():
    out = await list_branches(Ctx(Conn()), None)

    assert [b.code for b in out] == ["MAIN", "SHOP"]


@pytest.mark.asyncio
async def test_create_upper_cases_the_code():
    conn = Conn()

    out = await create_branch(Ctx(conn), BranchCreate(name="Uttara", code=" utt "), None)

    assert conn.inserted == [(TENANT, "Uttara", "UTT")]
    assert out.code == "UTT"
    assert out.is_main is False


@pytest.mark.asyncio
async def test_create_with_a_used_code_is_409():
    with pytest.raises(HTTPException) as exc:
        await create_branch(Ctx(Conn()), BranchCreate(name="Other", code="shop"), None)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_renames_and_deactivates():
    conn = Conn()

    out = await update_branch(Ctx(conn), SHOP, BranchUpdate(name="Shop 2", is_active=False), None)

    assert out.name == "Shop 2"
    assert out.is_active is False


@pytest.mark.asyncio
async def test_main_branch_cannot_be_deactivated():
    conn = Conn()

    with pytest.raises(HTTPException) as exc:
        await update_branch(Ctx(conn), MAIN, BranchUpdate(is_active=False), None)

    assert exc.value.status_code == 400
    assert conn.rows[MAIN]["is_active"] is True


@pytest.mark.asyncio
async def test_branch_holding_stock_cannot_be_deactivated():
    # Transfers refuse inactive branches, so its stock could never be moved out.
    conn = Conn(held=3)

    with pytest.raises(HTTPException) as exc:
        await update_branch(Ctx(conn), SHOP, BranchUpdate(is_active=False), None)

    assert exc.value.status_code == 409
    assert conn.rows[SHOP]["is_active"] is True


@pytest.mark.asyncio
async def test_main_branch_can_be_renamed():
    out = await update_branch(Ctx(Conn()), MAIN, BranchUpdate(name="Head office"), None)

    assert out.name == "Head office"


@pytest.mark.asyncio
async def test_update_unknown_branch_is_404():
    with pytest.raises(HTTPException) as exc:
        await update_branch(Ctx(Conn()), UUID(int=0xFF), BranchUpdate(name="x"), None)

    assert exc.value.status_code == 404


def test_blank_name_or_code_is_rejected():
    with pytest.raises(ValueError):
        BranchCreate(name=" ", code="X")
    with pytest.raises(ValueError):
        BranchCreate(name="X", code="")
