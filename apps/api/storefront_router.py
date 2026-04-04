from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from tenant import resolve_tenant_id, subdomain_from_request

router = APIRouter(prefix="/v1/storefront", tags=["storefront"])


@router.get("/products")
async def storefront_products(request: Request):
    """Public storefront products (no auth, filtered by tenant)."""
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    # Placeholder: return public products
    return {"tenant": sub, "products": []}