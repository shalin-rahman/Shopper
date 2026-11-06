# Review Remediation (2026-10-23 audit) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the confirmed bugs from the 2026-10-23 whole-system review that need no product decision, and list the rest as decision-gated follow-ups.

**Architecture:** Small, local fixes in the FastAPI routers and services, one forward migration (`027_review_hardening.sql`) for DB-side fixes, one script so a fresh Postgres container applies all migrations, and one mobile payload fix. No new layers.

**Tech Stack:** FastAPI + asyncpg (Python 3.14, pytest, asyncio_mode=auto), PostgreSQL 16 with RLS, Flutter/Drift (mobile).

**Spec:** `.specify/specs/shopper-platform/spec.md` (requirements REQ-BR-001..010). The audit findings are summarised in the "Source findings" column of each task.

## Global Constraints

- Money is `Decimal` in Python and `NUMERIC` in SQL. No float math on the API side.
- Tenant data access goes through `ctx.transaction()` (shopper_app role, RLS). Platform-level writes go through `request.app.state.migrate_pool` (shopper_migrate, BYPASSRLS).
- Migrations are forward-only, numbered, and must be safe to re-run (`IF NOT EXISTS`, `DROP ... IF EXISTS` before `CREATE`).
- Unit tests live in `apps/api/tests/unit/` and must not need a database. Use fake conn/pool objects, as `tests/unit/test_pos_offline_validation.py` does.
- Run API tests from `apps/api` with `python -m pytest -q`. Baseline before this plan is 69 passed, 19 skipped.

## Review Focus

1. A tenant in `trialing` or `past_due` must be able to use the app, and a `suspended`, `canceled`, `deleted` or `pending` tenant must be refused. Task 1 tests both sides.
2. The API must refuse to start outside test mode with the default JWT secret. A dev who has not set `JWT_SECRET_KEY` gets a clear startup error, not a silent fallback. Task 2 tests it.
3. A storefront search for a product that is active but not opted in must return nothing. Task 3 tests it.
4. A pending payment older than the hold window must stop blocking the invoice balance. Task 4 tests it.
5. Business analytics with zero stock value must return 200 with turnover 0, not 500. Task 5 tests it.

---

### Task 1: Tenant onboarding works end to end

Source findings: `POST /v1/register` uses an undefined `pool` (500); new tenants are `trialing` but resolution only accepts `active` (404).

**Files:**
- Modify: `apps/api/routers/registration.py` (use the migrate pool)
- Modify: `apps/api/core/tenant_context.py:18-26` (`resolve_tenant_id`)
- Test: `apps/api/tests/unit/test_tenant_onboarding.py` (new)

**Interfaces:**
- Produces: `TRANSACTING_TENANT_STATUSES: tuple[str, ...] = ("active", "trialing", "past_due")` in `core/tenant_context.py`.
- `resolve_tenant_id(pool, subdomain)` queries `status = ANY($2::text[])` with `list(TRANSACTING_TENANT_STATUSES)`.
- `register_tenant` reads `request.app.state.migrate_pool`. It returns 503 "Registration unavailable" when the pool is `None`.

- [ ] **Step 1: Write failing tests**
  - `test_resolve_tenant_id_accepts_transacting_statuses`: a fake pool records `fetchrow` args. Assert the second arg equals `["active", "trialing", "past_due"]`.
  - `test_resolve_tenant_id_unknown_raises_404`: fake `fetchrow` returns `None`. Assert `HTTPException.status_code == 404`.
  - `test_register_without_migrate_pool_returns_503`: call `register_tenant` with `request.app.state.migrate_pool = None`. Assert 503.
  - `test_register_uses_migrate_pool`: the fake migrate pool's `fetchval` returns a UUID. Assert the response `status == "created"` and that the staff insert ran on that pool.
- [ ] **Step 2: Run** `python -m pytest tests/unit/test_tenant_onboarding.py -q`. Expected: FAIL (NameError / wrong args).
- [ ] **Step 3: Implement** the constant and query change, and switch registration to the migrate pool.
- [ ] **Step 4: Run** the new tests and the full suite. Expected: all pass.
- [ ] **Step 5: Commit** `fix(api): make tenant self-registration work and let trialing tenants sign in`.

### Task 2: Refuse insecure secrets at startup

Source findings: the JWT secret defaults to a known string; the admin key is compared with `!=`.

**Files:**
- Modify: `apps/api/core/config.py` (add the method)
- Modify: `apps/api/main.py` lifespan (call it after `get_settings()` when not testing)
- Modify: `apps/api/routers/admin.py:104-109` (`hmac.compare_digest`)
- Modify: `docker-compose.yml` api env (pass `JWT_SECRET_KEY`), `.env.example` (add `JWT_SECRET_KEY=`)
- Test: `apps/api/tests/unit/test_config_security.py` (new)

**Interfaces:**
- Produces: `DEFAULT_DEV_JWT_SECRET = "shopper-dev-secret-change-in-prod"` and `Settings.assert_safe_for_runtime() -> None`.
- `assert_safe_for_runtime` raises `RuntimeError` when `testing` is false and `jwt_secret_key` is empty, equals the default, or is shorter than 32 characters.

- [ ] **Step 1: Write failing tests**
  - `test_default_jwt_secret_rejected_outside_testing`
  - `test_short_jwt_secret_rejected`
  - `test_strong_secret_accepted`
  - `test_testing_mode_allows_default`
  - `test_require_admin_rejects_wrong_key`: 401.
  - `test_require_admin_accepts_right_key`
- [ ] **Step 2: Run.** Expected: FAIL (no method).
- [ ] **Step 3: Implement.** Do not change the conftest secret, since tests run with `TESTING=1`.
- [ ] **Step 4: Run** the full suite. Expected: all pass.
- [ ] **Step 5: Commit** `fix(api): refuse default JWT secret outside tests; constant-time admin key check`.

### Task 3: Storefront respects marketplace opt-in

Source finding: `GET /v1/storefront` lists every active product, ignoring `marketplace_enabled` (spec REQ-BR-009: "explicit product-level public opt-in").

**Files:**
- Modify: `apps/api/routers/storefront.py` (catalog count and list queries)
- Test: `apps/api/tests/unit/test_storefront_optin.py` (new)

- [ ] **Step 1: Write failing test.** `test_storefront_catalog_filters_on_marketplace_enabled` captures the SQL sent to a fake conn. Assert that both queries contain `p.marketplace_enabled = true`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Add `AND p.marketplace_enabled = true` to both queries.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `fix(api): storefront lists only marketplace-enabled products`.

### Task 4: Payment integrity

Source findings: pending payments reserve the balance forever (anyone can block an invoice via the public checkout); `order_id` is not unique, so a callback can hit the wrong row.

**Files:**
- Modify: `apps/api/services/payment_settlement.py` (`reserve_invoice_payment`)
- Modify: `apps/api/routers/payments.py` and `apps/api/routers/storefront.py` (catch `asyncpg.UniqueViolationError` on the payment insert and return 409)
- DB part: in Task 6 (unique index)
- Test: extend `apps/api/tests/unit/test_payment_ipn_replay.py`

**Interfaces:**
- Produces: `PENDING_PAYMENT_HOLD = timedelta(minutes=30)` in `services/payment_settlement.py`.
- In the reserved-sum SQL, pending rows count only when `created_at > now() - $2::interval`. Completed rows always count.

- [ ] **Step 1: Write failing test.** `test_reserve_counts_pending_only_inside_hold_window` uses a fake conn and asserts the reserved-sum query is passed `PENDING_PAYMENT_HOLD`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the full suite. Expected: PASS.
- [ ] **Step 5: Commit** `fix(api): expire pending payment holds; 409 on duplicate order_id`.

### Task 5: Report correctness

Source findings: business analytics divides by zero when stock value is 0; Mushak 6.10 drops walk-in sales (inner join on customers), includes cancelled and draft invoices, and hard-codes `end_date` to the 28th.

**Files:**
- Modify: `apps/api/routers/reports.py:169-173` and `:252-306`
- Test: `apps/api/tests/unit/test_reports_core.py` (new)

**Interfaces:**
- Produces: `_inventory_turnover(cogs_annual: Decimal, avg_inv_value: Decimal) -> Decimal`, which returns `Decimal("0")` when `avg_inv_value <= 0`.
- 6.10 uses `LEFT JOIN customers`, `COALESCE(c.name_en, i.buyer_name_en)`, `i.status NOT IN ('draft','cancelled')`, and `end_date = date(year, month, calendar.monthrange(year, month)[1])`.

- [ ] **Step 1: Write failing tests**
  - `test_turnover_zero_inventory_returns_zero`
  - `test_turnover_normal`: `_inventory_turnover(Decimal("1200"), Decimal("300")) == Decimal("4")`.
  - `test_mushak_6_10_sql_includes_walk_in_and_excludes_drafts`: fake conn captures the SQL. Assert `LEFT JOIN` and the status filter.
  - `test_mushak_6_10_end_date_is_month_end`: February 2028 gives the 29th.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `fix(api): analytics zero-stock crash and Mushak 6.10 coverage`.

### Task 6: DB hardening migration and fresh-init migrations

Source findings: FORCE RLS is missing on 10 tables; the audit hash chain forks under concurrent or same-transaction inserts; admin tenant-status changes are not audited; `order_id` is not unique; `database/init/02_apply_migrations.sh` is empty, so a fresh container lacks invoices and stock tables.

**Files:**
- Create: `database/migrations/027_review_hardening.sql`
- Modify: `database/init/02_apply_migrations.sh` (currently 0 bytes)
- Modify: `apps/api/routers/admin.py` `set_tenant_status` (write an audit row in the same transaction)
- Test: `apps/api/tests/unit/test_migration_027.py` (new, static checks); `apps/api/tests/unit/test_admin_audit.py` (new)

**027 contents (decisions):**
- `ALTER TABLE ... FORCE ROW LEVEL SECURITY` for: suppliers, purchase_orders, po_lines, expense_categories, expenses, customer_collections, accounts, account_transfers, supplier_payments.
- `ALTER TABLE tenant_data.audit_log ADD COLUMN IF NOT EXISTS chain_seq BIGINT GENERATED ALWAYS AS IDENTITY`. This only adds the column if it is missing.
- Replace `chain_audit_hash()` so it first runs `PERFORM pg_advisory_xact_lock(hashtextextended(NEW.tenant_id::text, 0))`, then reads the previous hash `ORDER BY chain_seq DESC LIMIT 1`. `chain_seq` is assigned before BEFORE triggers run, so it orders rows inserted in the same transaction.
- Payment `order_id` uniqueness, done in two steps:
  - A `DO` block raises a clear error if duplicates exist in `(tenant_id, gateway, order_id)` where `order_id IS NOT NULL`.
  - Then `CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_tenant_gateway_order ON tenant_data.payments (tenant_id, gateway, order_id) WHERE order_id IS NOT NULL`.

**02_apply_migrations.sh:** a POSIX `sh` script run by the postgres image on first init. It applies `/migrations/[0-9]*.sql` in sort order with `psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f`. It skips silently if `/migrations` is not mounted.

**Admin audit row:** `INSERT INTO tenant_data.audit_log (tenant_id, table_name, record_id, action, old_values, new_values, changed_by) VALUES ($1, 'platform.tenants', $1, 'UPDATE', jsonb_build_object('status', <old>), jsonb_build_object('status', <new>), 'platform-admin')`. Read the old status with `SELECT ... FOR UPDATE` inside `conn.transaction()`.

- [ ] **Step 1: Write failing tests**
  - `test_027_forces_rls_on_all_listed_tables`: each table name appears with `FORCE ROW LEVEL SECURITY`.
  - `test_027_audit_chain_uses_lock_and_seq`
  - `test_027_payment_order_unique_index`
  - `test_init_apply_script_not_empty`
  - `test_set_tenant_status_writes_audit_row`: the fake migrate pool records the executed SQL. Assert an `audit_log` insert with old and new status.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the full suite. Expected: PASS.
- [ ] **Step 5 (needs Docker running):**
  - `docker compose up -d postgres` on a fresh volume, then check that `\dt tenant_data.*` lists invoices and stock_transactions.
  - Run `INTEGRATION_TEST=1 DATABASE_URL=... python -m pytest tests/integration -q`.
  - Expected: the RLS isolation tests run and pass. If Docker is not available, record this step as not done.
- [ ] **Step 6: Commit** `fix(db): force RLS, serialise audit chain, unique payment order ids, apply migrations on init`.

### Task 7: Mobile sends 2-decimal money

Source finding: mobile stores money as `double`; an unrounded value such as `33.330000000000005` fails the API's `decimal_places=2` check and rejects the whole order.

**Files:**
- Modify: `shopper-mobile/lib/data/repositories/order_repository_impl.dart` (sync payload around lines 210-232)
- Test: `shopper-mobile/test/` (existing order repository test file)

**Interfaces:**
- Produces: a private helper `String _money(double v) => v.toStringAsFixed(2);`. It is applied to total, subtotal, discount, taxAmount, amount_paid (when non-null) and the item unitPrice, discount, taxAmount and vatAmount. The API accepts strings for `Decimal`.

- [ ] **Step 1: Write failing test.** `sync payload rounds money to 2 decimals`: an order with `amountPaid = 33.330000000000005` produces a payload with `'amount_paid': '33.33'`.
- [ ] **Step 2: Run** `flutter test`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `flutter test` and `flutter analyze`. Expected: pass, no issues.
- [ ] **Step 5: Commit** `fix(mobile): send money as 2-decimal strings in POS sync`.

---

## Phase 2: needs a product decision first (not in this plan)

Each item below needs an answer before a plan can be written.

| Finding | Decision needed |
|---|---|
| Manual `POST /invoices` never reduces stock or writes the VAT register | Add an "issue" step (`POST /invoices/{id}/issue`) that locks stock, reduces it and writes Mushak 6.3 lines? Or should creating the invoice do it? |
| Credit notes write no negative VAT line and returns stay in COGS | Which Mushak form for credit notes (6.7)? That needs a CHECK change on `vat_sales_register_lines`. |
| Branch transfer reduces global stock and the receiving branch gets nothing | Build location-level stock balances (new table), or block transfers until then? |
| Public `GET /v1/storefront/checkout/{id}` shows any invoice by UUID | Use a signed payment link token, or require customer login? |
| `X-Shopper-Tenant` overrides the host, and `localhost` / IP maps to `demo` | Restrict both to dev mode? Mobile and web dev rely on them today. |
| No tenant product search; no web pages for reports, marketplace or payments; no `marketplace_enabled` toggle in the web UI | Which screens come first? |
| Rocket gateway returns 501; bKash and Nagad fail closed | Waiting on provider API contracts. |
| spec.md lacks the NFR sections, procurement, accounting and expenses; docs/TODO.md is out of date | Docs refresh, can be done any time. |

## Phase 2 decisions (2026-10-23)

Work order: small risks first.

1. **Checkout link.** `GET /v1/storefront/checkout/{id}` requires a signed token: an HMAC of `invoice_id|expiry` in `?t=..&e=..`. It returns 403 if the token is bad or expired. Guest checkout stays.
2. **Tenant override.** `X-Shopper-Tenant` and the localhost/IP fallback to `demo` work only when `ALLOW_TENANT_OVERRIDE=true` (default false). .env.example sets it true for local dev. docker-compose defaults to false.
3. **Invoice issue step.** `POST /invoices` creates a draft with no stock change. `POST /invoices/{id}/issue` locks stock, reduces it (409 if stock is short), writes the Mushak 6.3 lines, and sets the invoice to issued. Cancelling an issued invoice restores stock and writes reversing VAT lines.
4. **Credit notes.** Issuing one writes negative `vat_sales_register_lines` with form `6.7`, restocks the items, and takes their cost out of COGS. Needs a migration to widen the form CHECK.
5. **Per-branch stock.** Gets its own plan. New table `stock_levels(tenant_id, branch_id, product_id, qty)`. Existing stock moves to each tenant's main (first-created) branch. Every stock path becomes branch-scoped, and `products.stock_quantity` becomes the sum.
6. **Screens first:** marketplace toggle (per product and bulk), tenant product search, payments page. Reports pages come later.

Still waiting: Rocket/bKash/Nagad provider contracts; the spec and TODO docs refresh.
