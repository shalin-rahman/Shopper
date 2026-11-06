# Leftovers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the items left open after the per-branch stock work: broken purchase returns, legacy transfer code, branch limits for staff, noisy audit rows, and four missing features (web login, invoice actions, checkout page, refunds).

**Architecture:** One migration (031) carries every schema change. API changes stay in the routers that own them. The web app gets an auth service, a Bearer interceptor and a route guard, then the invoice actions and the public checkout page use them.

**Tech Stack:** FastAPI, asyncpg, Postgres RLS, Angular 17 standalone components with signals, Transloco, Tailwind shopper tokens.

**Spec:** the user's choices on 2026-10-23 ("LEFTOVERS AND REMAINNINGS"), plus docs/superpowers/plans/2026-10-23-per-branch-stock.md, whose "Known limits" section lists most of these items.

## Global Constraints

- No commit unless the user asks.
- Migrations are safe to rerun and run in one transaction. The next number is 031.
- Lock order for stock: `lock_products`, then `lock_levels`.
- Tests: `python -m pytest -q` in apps/api. Web: `npx ng test --watch=false --browsers=ChromeHeadless` and `npx ng build` in apps/shopper-web.
- UI uses the existing shopper tokens and `app-shopper-*` components, with strings in both en.json and bn.json.

## Review Focus

- Two purchase returns on the same PO on the same day must not collide on the `(tenant_id, note_no)` unique key.
- A cashier with no branch set must still be able to work, at the main branch.
- A stock-only change must still be audited, through the stock_transactions audit row.
- Refunds must never exceed the payment amount, even under two refunds at once.
- An expired token on the web must send the user to /login, not leave a broken page.

---

### Task 1: Checkout link refuses unpayable invoices — done

`create_checkout_link` and `get_invoice_qr` return 409 for draft and cancelled invoices (`_check_payable` in routers/invoices.py).

### Task 2: Migration 031 — done

**Files:** Create `database/migrations/031_leftovers.sql`. Test: `apps/api/tests/unit/test_migration_031.py` (static, like test_migration_030).

- debit_notes:
  - Add nullable `po_id` (FK purchase_orders) and `supplier_id` (FK suppliers).
  - Backfill them from `reference_id` where it names a PO.
  - Set defaults of 0 on the three amount columns.
  - Drop the duplicate policy `tenant_isolation_debit_notes`, recreate `tenant_isolation_dn` with WITH CHECK, and revoke DELETE.
- inventory_transfers: drop it only when it has no rows. Otherwise leave it and raise a NOTICE. Run under `SET LOCAL row_security = off`, so a role that RLS would filter gets an error instead of a false "empty".
- staff: add nullable `branch_id` (FK branches). NULL means the main branch.
- Audit: split `trg_audit_products` into an INSERT OR DELETE trigger and an UPDATE trigger with `WHEN ((to_jsonb(OLD) - 'stock_quantity') IS DISTINCT FROM (to_jsonb(NEW) - 'stock_quantity'))`.
- Refunds:
  - New table `payment_refunds`: id, tenant_id, payment_id, invoice_id, amount > 0, reference, note, credit_note_id, created_by, created_at.
  - RLS on, with SELECT and INSERT for shopper_app, plus an audit trigger.
  - `refresh_invoice_balance` subtracts refunds, and an AFTER INSERT trigger on `payment_refunds` calls it.

### Task 3: One purchase-return route — done

- Keep `POST /v1/tenant/suppliers/returns`, which has the VAT split. Delete `POST /v1/tenant/procurement/returns`.
- The kept route also:
  - writes `po_id` and `supplier_id`
  - lowers the PO's `total_amount` and `balance_due` by the total, VAT included, never below 0
  - builds `note_no` from the new note's own id, so two returns on the same PO and day do not collide.
- `GET /procurement/returns` keeps working; the web calls it. It reads `reference_id`, with `po_id` as a fallback.
- Delete the unused `InventoryTransferCreate` and `InventoryTransferOut` schemas.

### Task 4: Transfer by product_id — done

`StockTransferRequest` takes `product_id` or `sku`, exactly one, else 422. The route uses `lock_products`.

### Task 5: POS sync per branch — done

`/v1/tenant/pos/sync` takes `BranchDep` and returns that branch's `stock_levels.quantity` (0 when there is no row).

### Task 6: Branch limit — done

- `BranchChoice(branch_id, staff_uid=None)`. `current_branch` passes `staff_uid` for cashier and accountant only.
- `resolve()` with `staff_uid` set:
  - home = staff.branch_id, or the main branch when it is NULL
  - a header naming another branch gets 403
  - no header means home.
- The transfer source goes through the same rule.
- The staff create route accepts `branch_id`, and list shows it.

### Task 7: Web login (feature) — done

- `AuthService` in core/auth:
  - `login(username, password)` posts to `/api/v1/tenant/auth/login` and keeps the token in sessionStorage under `shopper.token`.
  - `logout()`.
  - `token` and `role` signals, decoded from the JWT payload. Exp is checked on read.
- `authInterceptor` adds `Authorization: Bearer` to `/api/v1/tenant` calls. On a 401 it logs out and goes to `/login`.
- `authGuard` protects every route except `/login` and `/checkout/:id`.
- A `/login` page with a username and password form. The nav gets a logout button.

### Task 8: Invoice issue and cancel (feature) — done

- `InvoiceService` with `list()`, `issue(id)`, `cancel(id)` and `checkoutLink(id)`.
- The invoices page has row actions:
  - Issue on draft
  - Cancel on draft or issued
  - Copy pay link on issued or partially_paid.
- A 409 shows the API detail in the row.

### Task 9: Public checkout page (feature) — done

- `/checkout/:id?t=&e=`, with no guard and no app shell.
- It loads `GET /api/v1/storefront/checkout/{id}?t&e` and shows the invoice and balance.
- The customer picks bKash, Nagad or SSLCommerz. The page POSTs `/pay` with the balance and redirects to `gateway_url`.
- A 403 means the link is bad or expired, and the page says so.

### Task 10: Refunds (feature) — done

- `POST /v1/tenant/payments/{id}/refunds` (ManagerDep):
  - body `{amount, reference?, note?, credit_note_id?}`
  - locks the payment row
  - 409 unless the payment is completed and the total refunded stays ≤ its amount
  - records `created_by` as the uid
- `GET /v1/tenant/payments/{id}/refunds`.
- The money goes back through the gateway's own dashboard. The gateway API has no refund call, so this records the refund and fixes the invoice balance.
- The web review page gets a refund amount and a "Record refund" action.

### Task 11: Close out — done

Run code-reviewer on 031, then the full suites and the build. Do a browser check of login, invoices and checkout. Run 027/030/031 on local Postgres if credentials are set. Update memory.

## Follow-ups done on 2026-10-24

- Migration 019: the po_lines policy used a tenant_id column that po_lines does not have. Fixed, with a test in test_migration_019.py.
- Printed invoice QR links last PRINTED_CHECKOUT_LINK_DAYS days (default 30, range 1 to 365). Screen links stay 24 hours.
- GET /payments/{id}/refunds returns 404 for an unknown payment.
- PATCH /products/{id} stock_quantity returns 409 when another branch holds stock, so one branch no longer takes the whole difference.
- GET /v1/tenant/settings fixed, and PATCH added (manager only, TenantSettingsUpdate).
- Migrations 01 to 031 applied on a local scratch Postgres 18.2. 027, 030 and 031 reran cleanly. A refund and RLS smoke test passed as shopper_app.

Still open items and handoff notes: see the "Review remediation and leftovers" section of .specify/specs/shopper-platform/tasks.md.
