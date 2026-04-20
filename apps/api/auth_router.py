from __future__ import annotations

import jwt
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import APIRouter, HTTPException, Request
from passlib.context import CryptContext
from pydantic import BaseModel

from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction

router = APIRouter(prefix="/v1/tenant/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In production these should come from environment variables
SECRET_KEY = "shopper-dev-secret-change-in-prod"
ALGORITHM = "HS256"

class LoginBody(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, body: LoginBody):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            "SELECT id, username, password_hash, role FROM tenant_data.staff WHERE username = $1 AND is_active = true",
            body.username
        )
        
        if not row or not pwd_context.verify(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({
        "uid": str(row["id"]),
        "tid": str(tenant_id),
        "role": row["role"]
    })
    
    return {"access_token": token, "token_type": "bearer"}
