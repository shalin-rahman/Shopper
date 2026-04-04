from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from schemas import CustomerCreate, CustomerOut, CustomerUpdate
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction

router = APIRouter(prefix="/v1/tenant/customers", tags=["customers"])


def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


@router.get("", response_model=list[CustomerOut])
async def list_customers(request: Request):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant_id = await resolve_tenant_id(pool, sub)
    async with tenant_transaction(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, code, name_en, name_bn, phone, email,
                   billing_address_en, billing_address_bn, created_at
            FROM tenant_data.customers
            ORDER BY code
            """
        )
    return [_row_to_out(r) for r in rows]


@router.post("", response_model=CustomerOut, status_code=201)
async def create_customer(request: Request, body: CustomerCreate):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant_id = await resolve_tenant_id(pool, sub)
    async with tenant_transaction(pool, tenant_id) as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO tenant_data.customers (
                    tenant_id, code, name_en, name_bn, phone, email,
                    billing_address_en, billing_address_bn
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, tenant_id, code, name_en, name_bn, phone, email,
                          billing_address_en, billing_address_bn, created_at
                """,
                tenant_id,
                body.code.strip(),
                body.name_en.strip(),
                body.name_bn.strip(),
                body.phone,
                body.email,
                body.billing_address_en,
                body.billing_address_bn,
            )
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=409, detail="Customer code already exists")
    return _row_to_out(row)


def _row_to_out(row: asyncpg.Record) -> CustomerOut:
    return CustomerOut(**dict(row))