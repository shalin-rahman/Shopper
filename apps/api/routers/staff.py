from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from core.tenant_context import TenantCtxDep
from core.dependencies import BranchChoice, StaffDep

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
async def create_staff(ctx: TenantCtxDep, body: dict, auth: StaffDep):
    if auth["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create staff")

    pwd_hash = pwd_context.hash(body.get("password"))
    try:
        branch_id = UUID(str(body["branch_id"])) if body.get("branch_id") else None
    except ValueError:
        raise HTTPException(status_code=400, detail="branch_id must be a UUID")

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
            ctx.tenant_id, body.get("username"), pwd_hash, body.get("full_name"), body.get("role", "cashier"),
            branch_id,
        )
    return dict(row)
