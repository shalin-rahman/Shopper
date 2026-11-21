from __future__ import annotations
import asyncpg
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from core.tenant_context import TenantCtxDep
from core.dependencies import BranchChoice, StaffDep
from schemas import StaffCreate

router = APIRouter(prefix="/v1/tenant/staff", tags=["management"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("")
async def list_staff(ctx: TenantCtxDep, _auth: StaffDep):
    from core.config import get_settings
    settings = get_settings()

    if ctx.dedicated_db is None and settings.testing:
        from utils.seed_loader import staff as seed_staff
        return {"items": seed_staff(ctx.subdomain or "demo")}

    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT id, username, full_name, role, is_active, branch_id FROM tenant_data.staff")
    return {"items": [dict(r) for r in rows]}

@router.post("", status_code=201)
async def create_staff(ctx: TenantCtxDep, body: StaffCreate, auth: StaffDep):
    if auth["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create staff")

    pwd_hash = pwd_context.hash(body.password)
    branch_id = body.branch_id
    try:
        async with ctx.transaction() as conn:
            # No branch_id means the main branch. A given one must be an active branch.
            if branch_id is not None:
                branch_id = await BranchChoice(branch_id).resolve(conn)
            row = await conn.fetchrow(
                """
                INSERT INTO tenant_data.staff (tenant_id, username, password_hash, full_name, role, branch_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, username, role, branch_id
                """,
                ctx.tenant_id, body.username, pwd_hash, body.full_name, body.role, branch_id,
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Username already exists")
    return dict(row)
