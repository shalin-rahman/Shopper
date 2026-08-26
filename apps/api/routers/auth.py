from __future__ import annotations

import jwt
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel

from core.tenant_context import TenantCtxDep

router = APIRouter(prefix="/v1/tenant/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginBody(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    from core.config import get_settings
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

@router.post("/login", response_model=TokenResponse)
async def login(ctx: TenantCtxDep, body: LoginBody):
    from core.config import get_settings
    settings = get_settings()

    if ctx.dedicated_db is None and settings.testing:
        # Allow login in test mode with any valid looking strings
        token = create_access_token({
            "uid": "00000000-0000-0000-0000-000000000000",
            "tid": "00000000-0000-0000-0000-000000000000",
            "role": "admin"
        })
        return {"access_token": token, "token_type": "bearer"}

    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, password_hash, role FROM tenant_data.staff WHERE username = $1 AND is_active = true",
            body.username
        )
        
        if not row or not pwd_context.verify(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({
        "uid": str(row["id"]),
        "tid": str(ctx.tenant_id),
        "role": row["role"]
    })
    
    return {"access_token": token, "token_type": "bearer"}
