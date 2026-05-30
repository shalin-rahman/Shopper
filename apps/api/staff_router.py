from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from passlib.context import CryptContext
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from deps import StaffDep

router = APIRouter(prefix="/v1/tenant/staff", tags=["management"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("")
async def list_staff(request: Request, _auth: StaffDep):
    sub = subdomain_from_request(request)
    pool = request.app.state.db_pool
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch("SELECT id, username, full_name, role, is_active FROM tenant_data.staff")
    return {"items": [dict(r) for r in rows]}

@router.post("", status_code=201)
async def create_staff(request: Request, body: dict, auth: StaffDep):
    if auth["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create staff")

    sub = subdomain_from_request(request)
    pool = request.app.state.db_pool
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    pwd_hash = pwd_context.hash(body.get("password"))
    
    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.staff (tenant_id, username, password_hash, full_name, role)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, username, role
            """,
            tenant_id, body.get("username"), pwd_hash, body.get("full_name"), body.get("role", "cashier")
        )
    return dict(row)
