"""FastAPI dependency aliases — prefer Depends() over calling get_settings() inside route bodies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from config import Settings, get_settings


def configure_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(configure_settings)]


import jwt
from typing import Any
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

auth_scheme = HTTPBearer()

# IMPORTANT: These must match auth_router.py. In production, use shared config.
SECRET_KEY = "shopper-dev-secret-change-in-prod"
ALGORITHM = "HS256"

def has_role(allowed_roles: list[str]):
    async def dependency(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> dict[str, Any]:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            role = payload.get("role")
            if role not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return payload
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    return dependency

StaffDep = Annotated[dict[str, Any], Depends(has_role(["admin", "manager", "accountant", "cashier"]))]
AccountantDep = Annotated[dict[str, Any], Depends(has_role(["admin", "manager", "accountant"]))]
ManagerDep = Annotated[dict[str, Any], Depends(has_role(["admin", "manager"]))]
AdminDep = Annotated[dict[str, Any], Depends(has_role(["admin"]))]
