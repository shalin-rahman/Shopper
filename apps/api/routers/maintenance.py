from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from core.tenant_context import TenantCtxDep
from core.dependencies import ManagerDep

router = APIRouter(prefix="/v1/tenant/maintenance", tags=["ops"])

@router.post("/ledger-reconcile")
async def reconcile_ledger_balances(request: Request, _auth: ManagerDep):
    """
    Recalculates account balances from ledger history to fix any drift.
    """
    sub = subdomain_from_request(request)
    tenant = await resolve_tenant_id(pool, sub)
    tenant_id = tenant["id"]

    async with tenant_transaction(request, tenant_id, tenant["dedicated_database_name"]) as conn:
        # Reset all balances to zero
        await conn.execute("UPDATE tenant_data.accounts SET current_balance = 0")
        
        # Aggregate from ledger
        recalc = await conn.fetch(
            """
            SELECT account_code, SUM(debit - credit) as net_balance
            FROM tenant_data.ledger_entries
            GROUP BY account_code
            """
        )
        
        for row in recalc:
            await conn.execute(
                "UPDATE tenant_data.accounts SET current_balance = $1 WHERE code = $2",
                row["net_balance"], row["account_code"]
            )
            
    return {"status": "success", "accounts_reconciled": len(recalc)}

@router.get("/health")
async def health_check(request: Request):
    """
    Verifies tenant database and cache connectivity.
    """
    sub = subdomain_from_request(request)
    try:
        tenant = await resolve_tenant_id(pool, sub)
        async with tenant_transaction(request, tenant["id"], tenant["dedicated_database_name"]) as conn:
            await conn.execute("SELECT 1")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Tenant health check failed: {str(e)}")
    
    return {"status": "healthy", "tenant": sub}
