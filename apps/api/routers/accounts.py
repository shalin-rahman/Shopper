from __future__ import annotations
from fastapi import APIRouter, HTTPException
from core.tenant_context import TenantCtxDep
from core.dependencies import AccountantDep, StaffDep
from schemas import AccountTransferCreate

router = APIRouter(prefix="/v1/tenant/accounts", tags=["accounting"])

@router.get("")
async def list_accounts(ctx: TenantCtxDep, _auth: StaffDep):
    from core.config import get_settings
    settings = get_settings()

    if ctx.dedicated_db is None and settings.testing:
        from utils.seed_loader import accounts as seed_accounts
        return {"items": seed_accounts(ctx.subdomain or "demo")}

    async with ctx.transaction() as conn:
        rows = await conn.fetch("SELECT * FROM tenant_data.accounts ORDER BY code")
    return {"items": [dict(r) for r in rows]}

@router.post("/transfer", status_code=201)
async def transfer_funds(ctx: TenantCtxDep, body: AccountTransferCreate, auth: AccountantDep):
    """
    Moves money between the business's own accounts (e.g. Cash to Bank).
    """
    from_code = body.from_account_code
    to_code = body.to_account_code
    amount = body.amount

    async with ctx.transaction() as conn:
        # Verify accounts exist
        from_acc = await conn.fetchrow("SELECT id FROM tenant_data.accounts WHERE code = $1", from_code)
        to_acc = await conn.fetchrow("SELECT id FROM tenant_data.accounts WHERE code = $1", to_code)
        
        if not from_acc or not to_acc:
            raise HTTPException(status_code=404, detail="Account(s) not found")

        # 1. Record Transfer
        tx_id = await conn.fetchval(
            """
            INSERT INTO tenant_data.account_transfers (tenant_id, from_account_id, to_account_id, amount, description, staff_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            ctx.tenant_id, from_acc["id"], to_acc["id"], amount, body.description, auth["uid"]
        )
        
        # 2. Update Ledger (Double Entry)
        # Credit the source (Decrease Asset)
        await conn.execute(
            """
            INSERT INTO tenant_data.ledger_entries (tenant_id, account_code, credit, description, reference_type, reference_id)
            VALUES ($1, $2, $3, $4, 'transfer', $5)
            """,
            ctx.tenant_id, from_code, amount, f"Transfer to {to_code}", tx_id
        )
        
        # Debit the destination (Increase Asset)
        await conn.execute(
            """
            INSERT INTO tenant_data.ledger_entries (tenant_id, account_code, debit, description, reference_type, reference_id)
            VALUES ($1, $2, $3, $4, 'transfer', $5)
            """,
            ctx.tenant_id, to_code, amount, f"Transfer from {from_code}", tx_id
        )

    return {"status": "success", "transfer_id": str(tx_id)}
