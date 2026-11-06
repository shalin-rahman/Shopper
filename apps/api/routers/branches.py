from __future__ import annotations
from datetime import datetime
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from core.tenant_context import TenantCtxDep
from core.dependencies import AdminDep, StaffDep

router = APIRouter(prefix="/v1/tenant/branches", tags=["branches"])


class BranchCreate(BaseModel):
    name: str = Field(..., max_length=120)
    code: str = Field(..., max_length=20)

    @field_validator("name", "code")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value.strip() if value else value


class BranchOut(BaseModel):
    id: UUID
    name: str
    code: str
    is_main: bool
    is_active: bool
    created_at: datetime


@router.get("", response_model=list[BranchOut])
async def list_branches(ctx: TenantCtxDep, _auth: StaffDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch(
            "SELECT * FROM tenant_data.branches ORDER BY is_main DESC, name"
        )
    return [BranchOut(**dict(r)) for r in rows]


@router.post("", response_model=BranchOut, status_code=201)
async def create_branch(ctx: TenantCtxDep, body: BranchCreate, _auth: AdminDep):
    async with ctx.transaction() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO tenant_data.branches (tenant_id, name, code)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                ctx.tenant_id,
                body.name,
                body.code.upper(),
            )
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=409, detail="A branch with this code already exists")
    return BranchOut(**dict(row))


@router.patch("/{branch_id}", response_model=BranchOut)
async def update_branch(ctx: TenantCtxDep, branch_id: UUID, body: BranchUpdate, _auth: AdminDep):
    async with ctx.transaction() as conn:
        current = await conn.fetchrow(
            "SELECT is_main FROM tenant_data.branches WHERE id = $1 FOR UPDATE",
            branch_id,
        )
        if not current:
            raise HTTPException(status_code=404, detail="Branch not found")
        # Requests with no X-Shopper-Branch header use the main branch, so it must stay active.
        if current["is_main"] and body.is_active is False:
            raise HTTPException(status_code=400, detail="The main branch cannot be deactivated")
        # Transfers refuse inactive branches, so stock left here could never be moved out.
        if body.is_active is False and await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM tenant_data.stock_levels WHERE branch_id = $1 AND quantity <> 0)",
            branch_id,
        ):
            raise HTTPException(status_code=409, detail="Move this branch's stock out before deactivating it")

        row = await conn.fetchrow(
            """
            UPDATE tenant_data.branches
            SET name = COALESCE($2, name), is_active = COALESCE($3, is_active), updated_at = now()
            WHERE id = $1
            RETURNING *
            """,
            branch_id,
            body.name,
            body.is_active,
        )
    return BranchOut(**dict(row))
