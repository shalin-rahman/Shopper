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
    async def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme),
    ) -> dict[str, Any]:
        from core.config import get_settings
        from core.tenant_context import resolve_tenant_ctx, subdomain_from_request

        settings = get_settings()
        
        if not credentials:
            sub = subdomain_from_request(request)
            if settings.testing and (
                sub == "demo" or "localhost" in request.headers.get("host", "")
            ):
                ctx = await resolve_tenant_ctx(request, settings)
                return {
                    "sub": "dev-guest",
                    "role": "admin",
                    "tenant_id": str(ctx.tenant_id),
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
            ctx = await resolve_tenant_ctx(request, settings)
            if str(payload.get("tid") or "") != str(ctx.tenant_id):
                raise HTTPException(
                    status_code=403,
                    detail="Token tenant does not match the requested tenant",
                )
            return payload
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    return dependency

StaffDep = Annotated[dict[str, Any], Depends(has_role(["admin", "manager", "accountant", "cashier"]))]
AccountantDep = Annotated[dict[str, Any], Depends(has_role(["admin", "manager", "accountant"]))]
ManagerDep = Annotated[dict[str, Any], Depends(has_role(["admin", "manager"]))]
AdminDep = Annotated[dict[str, Any], Depends(has_role(["admin"]))]
