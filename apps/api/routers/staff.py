from __future__ import annotations
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from core.tenant_context import TenantCtxDep
from core.dependencies import StaffDep

router = APIRouter(prefix="/v1/tenant/staff", tags=["management"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("")
async def list_staff(ctx: TenantCtxDep, _auth: StaffDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT id, username, full_name, role, is_active FROM tenant_data.staff")
    return {"items": [dict(r) for r in rows]}

@router.post("", status_code=201)
async def create_staff(ctx: TenantCtxDep, body: dict, auth: StaffDep):
    if auth["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create staff")

    pwd_hash = pwd_context.hash(body.get("password"))
    
    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.staff (tenant_id, username, password_hash, full_name, role)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, username, role
            """,
            ctx.tenant_id, body.get("username"), pwd_hash, body.get("full_name"), body.get("role", "cashier")
        )
    return dict(row)
