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
from uuid import UUID
from fastapi import Header, HTTPException, Request

from services.stock import main_branch_id
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
            if settings.testing and (
                subdomain_from_request(request) == "demo"
                or "localhost" in request.headers.get("host", "")
            ):
                ctx = await resolve_tenant_ctx(request, settings)
                return {
                    "sub": "dev-guest",
                    "uid": "00000000-0000-0000-0000-000000000000",
                    "tid": str(ctx.tenant_id),
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


class BranchChoice:
    """The branch a request works on. resolve() checks it inside the caller's RLS transaction."""

    def __init__(self, branch_id: UUID | None, staff_uid: UUID | None = None):
        self.branch_id = branch_id
        # Set for roles that may only work at their own branch.
        self.staff_uid = staff_uid

    async def resolve(self, conn) -> UUID:
        branch_id = self.branch_id
        if self.staff_uid is not None:
            staff = await conn.fetchrow(
                "SELECT branch_id FROM tenant_data.staff WHERE id = $1", self.staff_uid
            )
            if staff is None:
                raise HTTPException(status_code=403, detail="Unknown staff member")
            # A staff member with no branch set works at the main branch.
            home = staff["branch_id"] or await main_branch_id(conn)
            if branch_id is not None and branch_id != home:
                raise HTTPException(status_code=403, detail="You can only work at your own branch")
            branch_id = home
        if branch_id is None:
            return await main_branch_id(conn)
        # RLS hides other tenants' branches, so they fail the same way as unknown ones.
        # FOR SHARE makes a deactivation wait until this transaction ends. Without it,
        # stock could be written to a branch that was deactivated mid-request.
        found = await conn.fetchval(
            "SELECT id FROM tenant_data.branches WHERE id = $1 AND is_active FOR SHARE",
            branch_id,
        )
        if found is None:
            raise HTTPException(status_code=400, detail="Unknown or inactive branch")
        return found


LIMITED_BRANCH_ROLES = ("cashier", "accountant")


def limited_staff_uid(auth: dict[str, Any]) -> UUID | None:
    """The staff id when this role is held to its own branch, else None."""
    if auth.get("role") in LIMITED_BRANCH_ROLES:
        return UUID(str(auth["uid"]))
    return None


def current_branch(auth: StaffDep, x_shopper_branch: str | None = Header(default=None)) -> BranchChoice:
    staff_uid = limited_staff_uid(auth)
    if not x_shopper_branch:
        return BranchChoice(None, staff_uid)
    try:
        return BranchChoice(UUID(x_shopper_branch), staff_uid)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Shopper-Branch must be a UUID")


BranchDep = Annotated[BranchChoice, Depends(current_branch)]
