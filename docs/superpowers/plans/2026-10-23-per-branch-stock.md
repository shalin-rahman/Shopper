# Per-Branch Stock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track stock per branch, move all existing stock to a main branch, and keep `products.stock_quantity` as the total.

**Architecture:** A new `branches` table and a `stock_levels` table (branch, product, quantity). Every stock write goes through one service function that changes `stock_levels`. A database trigger keeps `products.stock_quantity` equal to the sum across branches, so existing reads, reports and the mobile app keep working. Costing (FIFO layers and WAC) stays tenant-wide for now. Transfers move quantity between branches and do not touch cost layers.

**Tech Stack:** FastAPI, asyncpg, PostgreSQL with RLS, pytest with fake connections.

**Spec:** Phase 2 item 5 in `.specify/specs/shopper-platform/tasks.md` and the decisions in `project_review_remediation_2026_10.md` ("Build per-branch stock", "All to main branch").

## Global Constraints

- New tables follow the RLS form in `database/migrations/013_inventory_valuation.sql`: ENABLE and FORCE RLS, `tenant_isolation_<table>` policy with USING and WITH CHECK on `tenant_data.app_tenant_id()`, grants to shopper_app and shopper_migrate. Use `DROP POLICY IF EXISTS` first so the migration can be rerun.
- The migration is wrapped in BEGIN/COMMIT, is safe to rerun, and has a static test like `tests/unit/test_migration_027.py`.
- Quantities are NUMERIC(18,4) and never below 0 (`CHECK (quantity >= 0)`).
- Lock order: when one request locks several stock rows, lock them ordered by (branch_id, product_id).

## Decisions taken (change before starting if wrong)

1. **Which branch a request uses:** optional header `X-Shopper-Branch` (a branch id). It must belong to the tenant and be active, or the request gets 400. With no header, the main branch is used. Staff are not tied to a branch yet.
2. **Costing stays tenant-wide.** Per-branch FIFO needs branch_id on cost_layers and a trigger rewrite, and is left out.
3. **Transfers use new types `transfer_out` and `transfer_in`.** The FIFO trigger acts only on 'in' and 'out', so transfers leave cost layers and WAC alone.
4. **Storefront orders still do not take stock.** This was true before. It is reported as a separate gap.

## Review Focus

- A tenant with no main branch, for example one created after the migration but before the registration change is deployed. Expect: the stock service raises a clear 500 naming the tenant, not a NULL insert.
- A header naming another tenant's branch. Expect: 400, because RLS hides the row.
- A transfer to the same branch, or of more than the source holds. Expect: 400 and 409, and nothing written.
- Two POS sales for the same product at the same branch at once. Expect: one waits on the row lock, and the second fails with 409 if stock runs out.
- A rerun of migration 030 on a database where it already ran. Expect: no duplicate main branches and no doubled stock.

---

### Task 1: Migration 030 (branches, stock_levels, backfill, sum trigger)

**Files:**
- Create: `database/migrations/030_branch_stock.sql`
- Test: `apps/api/tests/unit/test_migration_030.py`

**Interfaces:**
- Produces:
  - `tenant_data.branches(id uuid pk, tenant_id, name text not null, code text not null, is_main bool not null default false, is_active bool not null default true, created_at, updated_at)`, with `UNIQUE (tenant_id, code)` and a partial unique index `ON (tenant_id) WHERE is_main`.
  - `tenant_data.stock_levels(tenant_id, branch_id fk, product_id fk, quantity NUMERIC(18,4) not null default 0 check >= 0, updated_at)`, with primary key (branch_id, product_id).
  - `stock_transactions.branch_id uuid` references branches. It stays nullable because old rows from deleted data may exist. It is backfilled to the main branch.
  - `stock_transactions_transaction_type_check` widened with `transfer_out` and `transfer_in`.
  - Trigger `trg_sync_product_stock` AFTER INSERT OR UPDATE OR DELETE on stock_levels. It sets `products.stock_quantity = SUM(quantity)` for the affected product.

- [ ] Step 1: Write the static tests. They should cover:
  - The main-branch insert is guarded by `WHERE NOT EXISTS (... is_main)`.
  - The stock_levels backfill uses `ON CONFLICT (branch_id, product_id) DO NOTHING`.
  - The RLS policy form is used for both tables.
  - The CHECK list includes the old ten types plus the two transfer types.
  - BEGIN/COMMIT is present.
- [ ] Step 2: Run `python -m pytest tests/unit/test_migration_030.py -q`. Expected: FAIL (file missing).
- [ ] Step 3: Write the migration. It must:
  - Create a main branch (code 'MAIN', name 'Main branch') for each tenant in `platform.tenants`.
  - Copy each product's `stock_quantity` into stock_levels for that tenant's main branch.
  - Set `stock_transactions.branch_id` to the main branch where it is NULL.
- [ ] Step 4: Run the tests. Expected: PASS.
- [ ] Step 5: Run the migration twice on a scratch database. Check that:
  - The second run changes nothing.
  - For every product, `SUM(stock_levels.quantity) = stock_quantity`.

### Task 2: Stock service

**Files:**
- Create: `apps/api/services/stock.py`
- Test: `apps/api/tests/unit/test_stock_service.py`

**Interfaces:**
- Produces:
  - `async def main_branch_id(conn) -> UUID`. Raises HTTPException 500 if the tenant has none.
  - `async def lock_levels(conn, branch_id: UUID, product_ids: list[UUID]) -> dict[UUID, Decimal]`. Locks the rows with FOR UPDATE, ordered by product_id. Missing rows count as 0.
  - `async def change_stock(conn, ctx, branch_id: UUID, product_id: UUID, delta: Decimal) -> None`. Does an upsert into stock_levels. If the result would be negative, it raises 409 "Insufficient stock at branch".
  - `async def record_movement(conn, ctx, branch_id, product_id, transaction_type, qty, reference_type, reference_id, notes, unit_cost=None, reason_code=None) -> None`. Inserts into stock_transactions with branch_id, then calls `change_stock` with the signed quantity. 'in', 'receive', 'return_in', 'gift_in' and 'transfer_in' are positive. The other types are negative. 'adjustment' takes a signed qty.

- [ ] Step 1: Write the tests:
  - Upsert SQL is used.
  - A negative result gives 409 and writes nothing.
  - A 'transfer_out' insert carries branch_id.
  - `main_branch_id` raises when there is no row.
- [ ] Step 2: Run them. Expected: FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run them. Expected: PASS.

### Task 3: Branch from the request

**Files:**
- Modify: `apps/api/core/dependencies.py`
- Test: `apps/api/tests/unit/test_branch_dep.py`

**Interfaces:**
- Produces: `BranchDep = Annotated[BranchChoice, Depends(current_branch)]`. `current_branch` reads `X-Shopper-Branch` and gives 400 if it is not a UUID. It does not touch the database. The router calls `await branch.resolve(conn)` inside its own RLS transaction. `resolve` returns the branch id if it is active and visible, otherwise 400. With no header it returns `main_branch_id(conn)`. This avoids a second connection per request.

- [x] Steps: write the failing tests (header ok, header malformed, header unknown, no header), then implement and run.

### Task 4: Move every stock write to the service

**Files (each currently writes `products.stock_quantity` directly):**
- `apps/api/routers/products.py`: opening stock on create, and the diff on update.
- `apps/api/routers/pos.py`: sale.
- `apps/api/routers/invoices.py`: `issue_invoice` and `_restock_at_sale_cost`.
- `apps/api/routers/procurement.py`: PO receive and purchase return.
- `apps/api/routers/suppliers.py`: return to supplier.
- `apps/api/routers/inventory.py`: manual in, out and adjust, plus gift, damage and expired.
- Tests to update:
  - Unit: `test_inventory_core.py`, `test_pos_offline_validation.py`, `test_invoice_issue.py` and `test_credit_note_vat.py`. These match the SQL `stock_quantity = stock_quantity ±`.
  - Integration: `tests/integration/test_pos_e2e.py` and `tests/api/test_inventory.py`.

- [x] Step 1: Update the fakes and asserts so they expect `record_movement` and `change_stock` SQL, with the branch taken from `BranchDep`. Run them. Expected: FAIL.
- [x] Step 2: In each router:
  - Add `branch: BranchDep`.
  - Replace the stock check with `lock_levels`.
  - Replace the stock_transactions insert and the products update with `record_movement`.
  - Leave the FIFO behaviour unchanged.
  - Invoices have no branch yet, so issue uses the main branch. A credit note restock goes back to the branch the sale rows left from, and to main when there are none. Only inventory, POS, procurement, suppliers and products take `BranchDep`.
- [x] Step 3: Run `python -m pytest -q`. Expected: all pass. Then run `grep -rn "stock_quantity = stock_quantity" apps/api/routers`. Expected: no matches.

Done notes:
- Procurement: `receive_po` now locks the PO row (`FOR UPDATE`), so two receives at once cannot both add stock.
- Both purchase-return endpoints (procurement `/returns` and suppliers `/returns`) parse items through `services.stock.return_items`, which rejects qty ≤ 0 and merges repeated products. The supplier one used to write a negative qty.
- Products: create inserts the product with 0 and records the opening stock as a movement (`reason_code` 'opening'). Update turns a new `stock_quantity` into an in/out movement of the difference (`reason_code` 'adjustment').
- Tests: `test_procurement_stock.py`, `test_product_stock.py`, plus `return_items` cases in `test_stock_service.py`.

### Task 5: Branches API and transfers

**Files:**
- Create: `apps/api/routers/branches.py` (GET list, POST create, PATCH name/is_active; admin role). Register it in `main.py`.
- Modify: `apps/api/routers/inventory.py` `POST /transfer`. The body becomes `{sku, qty, to_branch_id, from_branch_id (optional, main when missing), notes}`. It keeps `sku` to match `/receive` and `/adjust`.
- Modify: `apps/api/routers/registration.py`. Create the MAIN branch with the tenant.
- Tests: `tests/unit/test_branches.py`, `tests/unit/test_stock_transfer.py`, `tests/unit/test_tenant_onboarding.py`.

- [x] Step 1: Write the failing tests:
  - Transfer writes `transfer_out` at the source and `transfer_in` at the destination.
  - Both branches are locked in id order.
  - The same branch gives 400. Too little stock gives 409 with no writes.
  - The main branch cannot be deactivated (400).
  - Registration inserts a MAIN branch.
- [x] Step 2: Implement.
- [x] Step 3: Run `python -m pytest -q`. Expected: all pass. Result: 227 passed, 19 skipped.

Done notes:
- The `transfer_in` row has `reference_id` = the `transfer_out` id. The 6.5 PDF uses that link to print both branch names.
- GET `/branches` is open to all staff, so the POS can offer a branch picker. POST and PATCH are admin only.
- A branch that still holds stock cannot be deactivated (409). Transfers refuse inactive branches, so that stock could never be moved out.
- `database/seed_from_json.py` and `database/seed_sample.sql` now create the main branch and the `stock_levels` rows. They run after the migrations, so 030's backfill does not cover them.
- [x] Step 4: Run code-reviewer on migration 030, the service and the transfer.

Review notes (fixed, each with a unit test):
- Both purchase-return endpoints now lock the product rows (`services.stock.lock_products`) before any stock write. The stock_levels trigger updates the product row, so writing stock first and the product later could deadlock with a sale.
- `receive_po` reads PO lines in product order, for the same reason.
- `BranchChoice.resolve` takes the branch row `FOR SHARE`, so a branch cannot be deactivated while a request is writing stock to it.
- Migration 030 turns off the stock_transactions audit trigger during the branch_id backfill, so it does not write one audit row per old transaction.
- Migration 030 ends by setting each product total to the sum of its stock_levels rows, in case a rerun found drift.
- The 6.5 PDF only renders the sending side of a transfer (404 for any other transaction).

Review notes (known limits, not changed):
- Editing `stock_quantity` on a product applies the whole difference to one branch. A cut can fail with 409 even when the total across branches is enough. Fixed 2026-10-24: the edit now returns 409 when another branch holds stock.
- Any staff member can pick any active branch with the header. Staff are not tied to a branch yet. Fixed in 031: staff.branch_id limits cashiers and accountants.
- Every stock change now also writes a products audit row, through the sum trigger. Fixed in 031.
- No test runs 030, the trigger or the locks against a real Postgres. 030 was applied and rerun on a local scratch Postgres on 2026-10-24; there is still no automated test for it.

## Out of scope (reported to the user)

- Per-branch FIFO costing.
- Tying staff to a branch. Done later in 031.
- Branch on invoices and POS sales documents.
- A branches screen in shopper-web.
- Per-branch stock in the mobile app. Mobile keeps showing the total.
- Storefront orders not taking stock.
