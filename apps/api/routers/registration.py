from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from passlib.context import CryptContext
import asyncpg
from uuid import uuid4

router = APIRouter(prefix="/v1/register", tags=["onboarding"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterTenantBody(BaseModel):
    subdomain: str = Field(..., pattern="^[a-z0-9-]+$")
    company_name_en: str
    company_name_bn: str
    admin_username: str
    admin_password: str

@router.post("", status_code=201)
async def register_tenant(request: Request, body: RegisterTenantBody):
    """
    Self-service registration for new tenants.
    Creates the tenant record and the initial admin user.
    """
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Create Tenant
            try:
                tenant_id = await conn.fetchval(
                    """
                    INSERT INTO platform.tenants (subdomain, display_name_en, display_name_bn, status)
                    VALUES ($1, $2, $3, 'trialing')
                    RETURNING id
                    """,
                    body.subdomain.lower(), body.company_name_en, body.company_name_bn
                )
            except asyncpg.exceptions.UniqueViolationError:
                raise HTTPException(status_code=400, detail="Subdomain already taken")

            # 2. Create Tenant Settings
            await conn.execute(
                """
                INSERT INTO platform.tenant_settings (tenant_id, legal_title_en, legal_title_bn)
                VALUES ($1, $2, $3)
                """,
                tenant_id, body.company_name_en, body.company_name_bn
            )

            # 3. Create Admin Staff in the same schema (or dedicated if enabled)
            # Default to shared schema 'tenant_data' with GUC protection
            # Note: We need to set the tenant context to bypass RLS during setup or use shopper_migrate role.
            # For simplicity in this self-service, we insert into tenant_data.staff.
            
            pwd_hash = pwd_context.hash(body.admin_password)
            await conn.execute(
                """
                INSERT INTO tenant_data.staff (tenant_id, username, password_hash, full_name, role, is_active)
                VALUES ($1, $2, $3, $4, 'admin', true)
                """,
                tenant_id, body.admin_username, pwd_hash, body.company_name_en
            )

            # 4. Provision System Accounts (Chart of Accounts)
            await conn.execute("SELECT tenant_data.provision_system_accounts($1)", tenant_id)

    return {"status": "created", "subdomain": body.subdomain, "tenant_id": str(tenant_id)}
