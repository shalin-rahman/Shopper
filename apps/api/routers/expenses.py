from __future__ import annotations
import asyncpg
from fastapi import APIRouter, HTTPException
from core.tenant_context import TenantCtxDep
from core.dependencies import StaffDep
from schemas import ExpenseCreate

router = APIRouter(prefix="/v1/tenant/expenses", tags=["finance"])

@router.get("/categories")
async def list_categories(ctx: TenantCtxDep, _auth: StaffDep):
    from core.config import get_settings
    settings = get_settings()

    if ctx.dedicated_db is None and settings.testing:
        from utils.seed_loader import _tenant
        cats = _tenant(ctx.subdomain or "demo").get("accounting", {}).get("expenses", [])
        seen = list({e["category"] for e in cats})
        return {"items": [
            {"id": f"cat-{i}", "name_en": c, "name_bn": c, "code": c[:4].upper()}
            for i, c in enumerate(seen, start=1)
        ]}

    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT * FROM tenant_data.expense_categories ORDER BY name_en")
    return {"items": [dict(r) for r in rows]}

@router.get("")
async def list_expenses(ctx: TenantCtxDep, _auth: StaffDep):
    from core.config import get_settings
    settings = get_settings()

    if ctx.dedicated_db is None and settings.testing:
        from utils.seed_loader import expenses as seed_expenses
        return {"items": seed_expenses(ctx.subdomain or "demo")}

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
async def create_expense(ctx: TenantCtxDep, body: ExpenseCreate, auth: StaffDep):
    amount = body.amount
    try:
        async with ctx.transaction() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tenant_data.expenses (tenant_id, category_id, amount, description, staff_id)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, amount, created_at
                """,
                ctx.tenant_id, body.category_id, amount, body.description, auth["uid"]
            )

            # Log to ledger
            await conn.execute(
                """
                INSERT INTO tenant_data.ledger_entries (tenant_id, account_code, debit, description, reference_type, reference_id)
                VALUES ($1, 'EXPENSE', $2, $3, 'expense', $4)
                """,
                ctx.tenant_id, amount, body.description or "Business Expense", row["id"]
            )
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(status_code=404, detail="Expense category not found")

    return dict(row)
