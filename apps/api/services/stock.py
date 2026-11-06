"""Stock per branch.

Every stock change goes through here. stock_levels holds the quantity per branch;
a trigger keeps products.stock_quantity equal to the sum across branches.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException

# Types that add stock. 'adjustment' is signed by its qty; every other type takes stock.
_INWARD_TYPES = frozenset({"in", "receive", "return_in", "gift_in", "transfer_in"})


def return_items(items: list[dict]) -> list[tuple[UUID, Decimal]]:
    """Parse untyped {product_id, qty} items. Merges repeats and sorts by product so row locks come in order."""
    totals: dict[UUID, Decimal] = {}
    try:
        for item in items:
            product_id = UUID(str(item["product_id"]))
            qty = Decimal(str(item["qty"]))
            if not qty.is_finite() or qty <= 0:
                raise ValueError
            totals[product_id] = totals.get(product_id, Decimal("0")) + qty
    except (KeyError, TypeError, ValueError, ArithmeticError):
        raise HTTPException(status_code=400, detail="Each item needs a product_id and a qty above 0")
    return sorted(totals.items())


async def main_branch_id(conn) -> UUID:
    branch_id = await conn.fetchval(
        "SELECT id FROM tenant_data.branches WHERE is_main"
    )
    if branch_id is None:
        raise HTTPException(status_code=500, detail="Tenant has no main branch")
    return branch_id


async def lock_products(conn, product_ids) -> None:
    """Lock product rows in id order before any stock write.

    The stock_levels trigger updates the product row, so a path that skips this
    lock takes the stock row first and the product second, which is the
    opposite order to a sale and can deadlock with it.
    """
    ids = sorted(set(product_ids))
    if ids:
        await conn.fetch(
            "SELECT id FROM tenant_data.products WHERE id = ANY($1::uuid[]) ORDER BY id FOR UPDATE",
            ids,
        )


async def lock_levels(conn, branch_id: UUID, product_ids: list[UUID]) -> dict[UUID, Decimal]:
    """Lock the branch's rows for these products, in product order. A missing row counts as 0."""
    ordered = sorted(set(product_ids))
    rows = await conn.fetch(
        """
        SELECT product_id, quantity
        FROM tenant_data.stock_levels
        WHERE branch_id = $1 AND product_id = ANY($2::uuid[])
        ORDER BY product_id
        FOR UPDATE
        """,
        branch_id,
        ordered,
    )
    levels = {product_id: Decimal("0") for product_id in ordered}
    levels.update({row["product_id"]: Decimal(str(row["quantity"])) for row in rows})
    return levels


async def change_stock(conn, ctx, branch_id: UUID, product_id: UUID, delta: Decimal) -> None:
    if delta >= 0:
        await conn.execute(
            """
            INSERT INTO tenant_data.stock_levels (tenant_id, branch_id, product_id, quantity)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (branch_id, product_id) DO UPDATE
            SET quantity = tenant_data.stock_levels.quantity + EXCLUDED.quantity, updated_at = now()
            """,
            ctx.tenant_id,
            branch_id,
            product_id,
            delta,
        )
        return
    left = await conn.fetchval(
        """
        UPDATE tenant_data.stock_levels
        SET quantity = quantity + $3, updated_at = now()
        WHERE branch_id = $1 AND product_id = $2 AND quantity + $3 >= 0
        RETURNING quantity
        """,
        branch_id,
        product_id,
        delta,
    )
    if left is None:
        raise HTTPException(status_code=409, detail="Insufficient stock at branch")


def _signed(transaction_type: str, qty: Decimal) -> Decimal:
    if transaction_type == "adjustment" or transaction_type in _INWARD_TYPES:
        return qty
    return -qty


async def record_movement(
    conn,
    ctx,
    branch_id: UUID,
    product_id: UUID,
    transaction_type: str,
    qty: Decimal,
    reference_type: str | None,
    reference_id: UUID | None,
    notes: str | None,
    unit_cost: Decimal | None = None,
    reason_code: str | None = None,
) -> Any:
    """Change the branch level, then log the movement. Returns the stock_transactions row.

    The level changes first so a shortage raises 409 before anything is written.
    """
    await change_stock(conn, ctx, branch_id, product_id, _signed(transaction_type, qty))
    return await conn.fetchrow(
        """
        INSERT INTO tenant_data.stock_transactions (
            tenant_id, branch_id, product_id, transaction_type, quantity, unit_cost,
            reference_type, reference_id, notes, reason_code
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
        """,
        ctx.tenant_id,
        branch_id,
        product_id,
        transaction_type,
        qty,
        unit_cost,
        reference_type,
        reference_id,
        notes,
        reason_code,
    )
