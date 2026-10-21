from decimal import Decimal
from uuid import UUID

import asyncpg
from fastapi import HTTPException


async def reserve_invoice_payment(
    conn: asyncpg.Connection,
    invoice_id: UUID,
    amount: Decimal,
    currency: str,
) -> None:
    if currency != "BDT":
        raise HTTPException(
            status_code=400,
            detail="Invoice payments must use BDT",
        )

    invoice = await conn.fetchrow(
        """
        SELECT id, total_amount, status
        FROM tenant_data.invoices
        WHERE id = $1
        FOR UPDATE
        """,
        invoice_id,
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cancelled invoices cannot be paid")

    reserved = await conn.fetchval(
        """
        SELECT
            COALESCE((
                SELECT SUM(amount)
                FROM tenant_data.payments
                WHERE invoice_id = $1
                  AND status IN ('pending', 'completed')
            ), 0)
            +
            COALESCE((
                SELECT SUM(amount)
                FROM tenant_data.invoice_settlements
                WHERE invoice_id = $1
                  AND status = 'completed'
            ), 0)
        """,
        invoice_id,
    )
    available = Decimal(str(invoice["total_amount"])) - Decimal(str(reserved))
    if available <= 0:
        raise HTTPException(status_code=400, detail="Invoice has no remaining balance")
    if amount > available:
        raise HTTPException(
            status_code=400,
            detail="Payment amount exceeds the remaining invoice balance",
        )
