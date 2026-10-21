import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, model_validator

from core.tenant_context import TenantCtxDep
from core.dependencies import StaffDep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/tenant/pos", tags=["pos"])


class OfflinePunchLine(BaseModel):
    product_id: UUID = Field(validation_alias=AliasChoices("productId", "product_id"))
    product_name: str = Field(..., min_length=1, validation_alias=AliasChoices("productName", "product_name"))
    quantity: int = Field(..., gt=0, strict=True)
    unit_price: Decimal = Field(..., gt=0, validation_alias=AliasChoices("unitPrice", "unit_price"))
    vat_rate_pct: Decimal = Field(default=Decimal("0"), ge=0, validation_alias=AliasChoices("vatRatePct", "vat_rate_pct"))
    vat_amount: Decimal = Field(default=Decimal("0"), ge=0, validation_alias=AliasChoices("vatAmount", "vat_amount"))

    model_config = ConfigDict(populate_by_name=True)

    @property
    def line_total(self) -> Decimal:
        return (self.unit_price * Decimal(self.quantity)) + self.vat_amount


class OfflinePunchOrder(BaseModel):
    id: UUID | str = Field(...)
    order_number: str = Field(..., min_length=1, validation_alias=AliasChoices("orderNumber", "order_number"))
    total: Decimal = Field(..., gt=0)
    subtotal: Decimal = Field(..., ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0, validation_alias=AliasChoices("taxAmount", "tax_amount"))
    amount_paid: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=18,
        decimal_places=2,
        validation_alias=AliasChoices("amountPaid", "amount_paid"),
    )
    customer_name: str | None = Field(default=None, validation_alias=AliasChoices("customerName", "customer_name"))
    customer_phone: str | None = Field(default=None, validation_alias=AliasChoices("customerPhone", "customer_phone"))
    payment_method: Literal["cash", "bkash", "nagad", "rocket", "bank", "card", "credit", "other"] = Field(
        default="cash",
        validation_alias=AliasChoices("paymentMethod", "payment_method"),
    )
    items: list[OfflinePunchLine] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)

    @property
    def order_id(self) -> str:
        return str(self.id)

    @property
    def item_total(self) -> Decimal:
        return sum((item.line_total for item in self.items), Decimal("0"))

    @property
    def collected_amount(self) -> Decimal:
        return self.amount_paid if self.amount_paid is not None else Decimal("0")

    @model_validator(mode="after")
    def validate_totals(self):
        if self.items and self.subtotal < Decimal("0"):
            raise ValueError("subtotal must be non-negative")
        if self.discount > self.subtotal:
            raise ValueError("discount cannot exceed subtotal")
        if self.amount_paid is not None and self.amount_paid > self.total:
            raise ValueError("amount_paid cannot exceed order total")
        if self.payment_method == "credit" and self.collected_amount != 0:
            raise ValueError("credit orders cannot include a collected amount")
        if self.items:
            expected_subtotal = sum((item.unit_price * Decimal(item.quantity) for item in self.items), Decimal("0"))
            if abs(self.subtotal - expected_subtotal) > Decimal("0.01"):
                raise ValueError("subtotal does not match item totals")
            expected_tax = Decimal("0")
            for item in self.items:
                taxable = item.unit_price * Decimal(item.quantity)
                calculated_vat = (taxable * item.vat_rate_pct / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if abs(item.vat_amount - calculated_vat) > Decimal("0.01"):
                    raise ValueError(f"VAT amount does not match item VAT rate for {item.product_name}")
                expected_tax += item.vat_amount
            if abs(self.tax_amount - expected_tax) > Decimal("0.01"):
                raise ValueError("tax amount does not match item VAT amounts")
            expected_total = (self.subtotal + self.tax_amount) - self.discount
            if abs(self.total - expected_total) > Decimal("0.01"):
                raise ValueError("total does not match subtotal, tax and discount")
        return self


def parse_offline_punch_orders(payload: list[Any] | None) -> tuple[list[OfflinePunchOrder], list[dict[str, Any]]]:
    parsed: list[OfflinePunchOrder] = []
    rejected: list[dict[str, Any]] = []

    for raw_order in payload or []:
        if not isinstance(raw_order, dict):
            rejected.append({"local_id": None, "error": "Order must be an object"})
            continue

        try:
            order = OfflinePunchOrder.model_validate(raw_order)
        except ValidationError as exc:
            rejected.append({
                "local_id": raw_order.get("id"),
                "error": exc.errors(include_url=False),
            })
            continue

        if not order.items:
            rejected.append({
                "local_id": order.order_id,
                "error": [{"loc": ["items"], "msg": "Order must contain at least one item", "type": "value_error"}],
            })
            continue

        parsed.append(order)

    return parsed, rejected


class _AlreadySyncedOrder(Exception):
    pass


@router.get("/sync")
async def pos_sync_data(ctx: TenantCtxDep, _auth: StaffDep):
    """
    Returns a consolidated payload of products and categories for local mobile caching.
    """
    async with ctx.transaction() as conn:
        categories = await conn.fetch("SELECT id, name_en, name_bn FROM tenant_data.product_categories")
        products = await conn.fetch(
            """
            SELECT id, category_id, sku, name_en, name_bn, sell_price, vat_rate_pct, barcode, qr_payload, stock_quantity
            FROM tenant_data.products
            WHERE is_active = true
            """
        )

    return {
        "categories": [dict(c) for c in categories],
        "products": [dict(p) for p in products]
    }

@router.post("/offline-punch")
async def pos_offline_punch(ctx: TenantCtxDep, body: list[Any], _auth: StaffDep):
    """
    Processes a batch of offline-synced orders.
    Orchestrates Invoice -> Stock Transactions -> VAT Register population.
    """
    orders, rejected = parse_offline_punch_orders(body)
    synced_ids: list[str] = []

    async with ctx.transaction() as conn:
        for order in orders:
            try:
                async with conn.transaction():
                    existing = await conn.fetchrow(
                        """
                        SELECT id, invoice_no
                        FROM tenant_data.invoices
                        WHERE tenant_id = $1 AND source_order_id = $2
                        """,
                        ctx.tenant_id,
                        order.order_id,
                    )
                    if existing:
                        if existing["invoice_no"] != order.order_number:
                            raise ValueError("This local order ID was already synced with another invoice number")
                        raise _AlreadySyncedOrder

                    invoice_number = await conn.fetchrow(
                        """
                        SELECT id FROM tenant_data.invoices
                        WHERE tenant_id = $1 AND invoice_no = $2
                        """,
                        ctx.tenant_id,
                        order.order_number,
                    )
                    if invoice_number:
                        raise ValueError("Invoice number already exists")

                    demand_by_product: dict[UUID, int] = {}
                    for item in order.items:
                        demand_by_product[item.product_id] = (
                            demand_by_product.get(item.product_id, 0) + item.quantity
                        )
                    locked_products = await conn.fetch(
                        """
                        SELECT id, is_active, stock_quantity
                        FROM tenant_data.products
                        WHERE id = ANY($1::uuid[])
                        ORDER BY id
                        FOR UPDATE
                        """,
                        list(demand_by_product),
                    )
                    product_by_id = {product["id"]: product for product in locked_products}
                    for product_id, demanded_quantity in demand_by_product.items():
                        product = product_by_id.get(product_id)
                        if not product or not product["is_active"]:
                            raise ValueError(f"Product {product_id} is missing or inactive")
                        if Decimal(str(product["stock_quantity"])) < demanded_quantity:
                            raise ValueError(f"Insufficient stock for product {product_id}")

                    invoice_id = await conn.fetchval(
                        """
                        INSERT INTO tenant_data.invoices (
                            tenant_id, invoice_no, source_order_id, total_amount, subtotal, discount,
                            total_vat, buyer_name_en, phone, status, amount_paid, balance_due, notes, pos_tender
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'issued', 0, $4, $10, $11)
                        RETURNING id
                        """,
                        ctx.tenant_id,
                        order.order_number,
                        order.order_id,
                        order.total,
                        order.subtotal,
                        order.discount,
                        order.tax_amount,
                        order.customer_name,
                        order.customer_phone,
                        order.notes,
                        order.payment_method,
                    )
                    if order.collected_amount > 0:
                        await conn.execute(
                            """
                            INSERT INTO tenant_data.invoice_settlements (
                                tenant_id, invoice_id, amount, payment_method, source, source_reference
                            ) VALUES ($1, $2, $3, $4, 'pos', $5)
                            """,
                            ctx.tenant_id,
                            invoice_id,
                            order.collected_amount,
                            order.payment_method,
                            order.order_id,
                        )

                    discount_remaining = order.discount
                    for index, item in enumerate(order.items):
                        line_subtotal = item.unit_price * Decimal(item.quantity)
                        if index == len(order.items) - 1:
                            line_discount = discount_remaining
                        else:
                            line_discount = (
                                order.discount * line_subtotal / order.subtotal
                            ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                            discount_remaining -= line_discount

                        await conn.execute(
                            """
                            INSERT INTO tenant_data.invoice_lines (
                                tenant_id, invoice_id, product_id, description, qty, unit_price,
                                vat_rate_pct, vat_amount, line_total
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            """,
                            ctx.tenant_id,
                            invoice_id,
                            item.product_id,
                            item.product_name,
                            item.quantity,
                            item.unit_price,
                            item.vat_rate_pct,
                            item.vat_amount,
                            item.line_total,
                        )

                        await conn.execute(
                            """
                            INSERT INTO tenant_data.stock_transactions (
                                tenant_id, product_id, transaction_type, quantity, reference_type, reference_id, notes
                            ) VALUES ($1, $2, 'out', $3, 'sale', $4, $5)
                            """,
                            ctx.tenant_id,
                            item.product_id,
                            item.quantity,
                            invoice_id,
                            f"POS Sale: {order.order_number}",
                        )

                        await conn.execute(
                            "UPDATE tenant_data.products SET stock_quantity = stock_quantity - $1 WHERE id = $2",
                            item.quantity,
                            item.product_id,
                        )

                        await conn.execute(
                            """
                            INSERT INTO tenant_data.vat_sales_register_lines (
                                tenant_id, mushak_form, invoice_no, invoice_date,
                                buyer_name_en, description_en, qty, taxable_value, vat_amount,
                                discount_amount, total_amount
                            ) VALUES ($1, '6.3', $2, $3, $4, $5, $6, $7, $8, $9, $10)
                            """,
                            ctx.tenant_id,
                            order.order_number,
                            order.created_at.date() if order.created_at else datetime.now().date(),
                            order.customer_name,
                            item.product_name,
                            item.quantity,
                            line_subtotal,
                            item.vat_amount,
                            line_discount,
                            item.line_total - line_discount,
                        )

            except _AlreadySyncedOrder:
                synced_ids.append(order.order_id)
            except ValueError as exc:
                rejected.append({
                    "local_id": order.order_id,
                    "error": [{"loc": ["order"], "msg": str(exc), "type": "value_error"}],
                })
            except Exception:
                logger.exception("Error syncing order %s", order.order_id)
                rejected.append({
                    "local_id": order.order_id,
                    "error": [{
                        "loc": ["order"],
                        "msg": "Order could not be synced; retry later",
                        "type": "runtime_error",
                    }],
                })
            else:
                synced_ids.append(order.order_id)

    status = "success" if not rejected and len(synced_ids) == len(orders) else "partial_success" if synced_ids else "failed"
    return {
        "synced_count": len(synced_ids),
        "synced_local_ids": synced_ids,
        "rejected": rejected,
        "status": status,
    }
