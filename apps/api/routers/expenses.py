from __future__ import annotations
from decimal import Decimal
from fastapi import APIRouter, HTTPException
from core.tenant_context import TenantCtxDep
from core.dependencies import StaffDep

router = APIRouter(prefix="/v1/tenant/expenses", tags=["finance"])

@router.get("/categories")
async def list_categories(ctx: TenantCtxDep, _auth: StaffDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT * FROM tenant_data.expense_categories ORDER BY name_en")
    return {"items": [dict(r) for r in rows]}

@router.get("")
async def list_expenses(ctx: TenantCtxDep, _auth: StaffDep):
    async with ctx.transaction() as conn:
        rows = await conn.fetch(
            """
            SELECT e.*, c.name_en as category_name
            FROM tenant_data.expenses e
            JOIN tenant_data.expense_categories c ON e.category_id = c.id
            ORDER BY e.expense_date DESC, e.created_at DESC
            """
        )
    return {"items": [dict(r) for r in rows]}

@router.post("", status_code=201)
async def create_expense(ctx: TenantCtxDep, body: dict, auth: StaffDep):
    amount = Decimal(str(body.get("amount", 0)))
    cat_id = body.get("category_id")

    if not cat_id or amount <= 0:
        raise HTTPException(status_code=400, detail="Category and valid amount required")

    async with ctx.transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data.expenses (tenant_id, category_id, amount, description, staff_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, amount, created_at
            """,
            ctx.tenant_id, cat_id, amount, body.get("description"), auth["uid"]
        )
        
        # Log to ledger
        await conn.execute(
            """
            INSERT INTO tenant_data.ledger_entries (tenant_id, account_code, debit, description, reference_type, reference_id)
            VALUES ($1, 'EXPENSE', $2, $3, 'expense', $4)
            """,
            ctx.tenant_id, amount, body.get("description") or "Business Expense", row["id"]
        )

    return dict(row)
