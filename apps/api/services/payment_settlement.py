from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import asyncpg
from fastapi import HTTPException

# A pending gateway payment holds its share of the invoice balance only this
# long. After that an abandoned checkout no longer blocks a new payment.
PENDING_PAYMENT_HOLD = timedelta(minutes=30)


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
    if invoice["status"] == "draft":
        raise HTTPException(status_code=400, detail="Issue the invoice before taking payment")

    reserved = await conn.fetchval(
        """
        SELECT
            COALESCE((
                SELECT SUM(amount)
                FROM tenant_data.payments
                WHERE invoice_id = $1
                  AND (
                    status = 'completed'
                    OR (status = 'pending' AND created_at > now() - $2::interval)
                  )
            ), 0)
            +
            COALESCE((
                SELECT SUM(amount)
                FROM tenant_data.invoice_settlements
                WHERE invoice_id = $1
                  AND status = 'completed'
            ), 0)
            -
            -- Refunded money is free to pay again, as in refresh_invoice_balance (031).
            COALESCE((
                SELECT SUM(r.amount)
                FROM tenant_data.payment_refunds r
                JOIN tenant_data.payments p ON p.id = r.payment_id
                WHERE r.invoice_id = $1
                  AND p.status = 'completed'
            ), 0)
        """,
        invoice_id,
        PENDING_PAYMENT_HOLD,
    )
    available = Decimal(str(invoice["total_amount"])) - Decimal(str(reserved))
    if available <= 0:
        raise HTTPException(status_code=400, detail="Invoice has no remaining balance")
    if amount > available:
        raise HTTPException(
            status_code=400,
            detail="Payment amount exceeds the remaining invoice balance",
        )


async def late_settlement_problem(
    conn: asyncpg.Connection,
    invoice_id: UUID,
    amount: Decimal,
) -> str | None:
    """Say why a gateway payment about to complete needs a person to look at it.

    The gateway has already taken the money, so the payment is still recorded.
    This only flags an invoice that was cancelled meanwhile, or one this payment
    would overpay. Call it before marking the payment completed.
    """
    invoice = await conn.fetchrow(
        """
        SELECT status, total_amount, amount_paid
        FROM tenant_data.invoices
        WHERE id = $1
        FOR UPDATE
        """,
        invoice_id,
    )
    if not invoice:
        return None
    if invoice["status"] == "cancelled":
        return "invoice_cancelled"
    paid = Decimal(str(invoice["amount_paid"] or 0))
    if paid + amount > Decimal(str(invoice["total_amount"])):
        return "overpayment"
    return None
