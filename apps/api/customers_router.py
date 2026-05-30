from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from schemas import CustomerCreate, CustomerOut, CustomerUpdate, CustomerCollectionCreate, CustomerCollectionOut
from tenant import resolve_tenant_id, subdomain_from_request, tenant_transaction
from deps import StaffDep

router = APIRouter(prefix="/v1/tenant/customers", tags=["customers"])


def _pool(request: Request) -> asyncpg.Pool:
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return pool


@router.get("", response_model=list[CustomerOut])
async def list_customers(request: Request, _auth: StaffDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
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
async def create_customer(request: Request, body: CustomerCreate, _auth: StaffDep):
    sub = subdomain_from_request(request)
    if not sub:
        raise HTTPException(status_code=400, detail="Tenant subdomain required")

    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]
    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
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


@router.post("/collections", response_model=CustomerCollectionOut, status_code=201)
async def create_collection(request: Request, body: CustomerCollectionCreate, auth: StaffDep):
    """
    Records a payment from a customer to pay down their credit balance.
    """
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.customer_collections (
                tenant_id, customer_id, amount, payment_method, reference_no, notes, collected_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, customer_id, amount, payment_method, reference_no, notes, created_at
            """,
            tenant_id, body.customer_id, body.amount, body.payment_method,
            body.reference_no, body.notes, auth["uid"]
        )
    return CustomerCollectionOut(**dict(row))


@router.get("/collections", response_model=list[CustomerCollectionOut])
async def list_collections(request: Request, customer_id: UUID | None = None, _auth: StaffDep = None):
    """
    Lists customer collections history.
    """
    sub = subdomain_from_request(request)
    pool = _pool(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    query = "SELECT * FROM tenant_data.customer_collections WHERE tenant_id = $1"
    args = [tenant_id]
    
    if customer_id:
        query += " AND customer_id = $2"
        args.append(customer_id)
        
    query += " ORDER BY collection_date DESC, created_at DESC"

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        rows = await conn.fetch(query, *args)
    return [CustomerCollectionOut(**dict(r)) for r in rows]


def _row_to_out(row: asyncpg.Record) -> CustomerOut:
    return CustomerOut(**dict(row))