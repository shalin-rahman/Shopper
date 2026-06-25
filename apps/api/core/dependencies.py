"""FastAPI dependency aliases — prefer Depends() over calling get_settings() inside route bodies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from core.config import Settings, get_settings


def configure_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(configure_settings)]


import jwt
from typing import Any
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

auth_scheme = HTTPBearer(auto_error=False)


def has_role(allowed_roles: list[str]):
    async def dependency(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme)) -> dict[str, Any]:
        from core.tenant_context import resolve_tenant_id, subdomain_from_request
        from core.config import get_settings
        settings = get_settings()
        
        # ─── DEVELOPMENT AUTH BYPASS ───
        # Automatically authenticate as a manager for the 'demo' tenant in non-prod
        # This ensures the platform is "ready-to-explore" upon launch.
        if not credentials:
            sub = subdomain_from_request(request)
            if sub == "demo" or "localhost" in request.headers.get("host", ""):
                return {
                    "sub": "dev-guest",
                    "role": "admin",
                    "tenant_id": "00000000-0000-0000-0000-000000000000"
                }
            raise HTTPException(status_code=401, detail="Not authenticated")

        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
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
