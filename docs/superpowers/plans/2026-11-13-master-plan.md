# Master Implementation Plan (2026-11-13)

This is the only plan for the work left in Shopper. It replaces the "Still open" list in
[tasks.md](../../../.specify/specs/shopper-platform/tasks.md) as the place to pick work from.
The three 2026-10-23 plans are finished and kept as history.

## How to use this plan (read first, every session)

1. Read [AGENTS.md](../../../AGENTS.md), then this "How to use" section and the "Global rules". Nothing else is needed to start.
2. Take the first row in the **Tracker** whose status is `todo` and whose `Needs` are all `done`.
3. Read only that session's section. Do the steps in order. Each step names the files, the code and the test.
4. Run the session's **Verify** commands. Every check must pass. If one fails and the fix is outside the session's files, stop, set the row to `blocked`, and write the reason in the row.
5. Set the row to `done` and fill in the date and test counts. Do **not** edit other docs (README, DEPLOY, ARCHITECTURE_MAP, tasks.md, spec.md). Session G3 updates them once at the end. The only exception: a session that adds an env var also updates `.env.example` and `docs/DEPLOY.md` (said in the session).
6. Commit only when the user asks. Use one commit per session, message `<type>(<area>): <session id> <summary>`.

A session is sized for one sitting: at most about 6 files changed and one test file added. Do not merge sessions.

## Global rules

- **Never break what works.** Before the first edit, run the baseline command for the area you touch. The counts must not drop afterwards, except for tests the session deletes on purpose (it says so).
- **Baselines (updated 2026-11-27):** API unit `369 passed, 35 skipped`. API integration on shopper_verify `28 passed, 0 skipped`. Web on 2026-11-22: 97 unit tests passed, Playwright e2e 37 passed, `ng build` passes. Mobile: `flutter test` all pass and `flutter analyze` clean on 2026-10-24.
- **Commands**
  - API unit: `cd apps/api && python -m pytest -q`
  - API integration (scratch DB only): from `apps/api`, set `INTEGRATION_TEST=1`, `MIGRATE_DATABASE_URL` (superuser or migrate role), `DATABASE_URL` (login role that is a member of shopper_app, NOBYPASSRLS), `JWT_SECRET_KEY` (32+ chars), then `python -m pytest tests/integration -q`.
  - Web: `cd apps/shopper-web && npx ng test --watch=false --browsers=ChromeHeadless && npx ng build`
  - Mobile: `cd shopper-mobile && flutter test && flutter analyze`
  - Migrations on scratch DB: `python database/run_migrations.py` with `MIGRATE_DATABASE_URL` pointing at the scratch DB.
- **Databases:** use only the scratch DB `shopper_verify`. Never `shopper`, `ShoppersDB`, or any Neon URL.
- **Migrations:** numbered SQL in `database/migrations`, one `BEGIN; … COMMIT;`, safe to rerun, first line a `--` comment. 032, 033 and 035 are done. **034** is kept for F2; any other new migration takes **036**. Each new migration gets a static test `apps/api/tests/unit/test_migration_0NN.py` in the style of `test_migration_031.py`.
- **Locks:** lock product rows (`services.stock.lock_products`) before `lock_levels`. A tenant-row lock taken before an audit insert uses `FOR NO KEY UPDATE`.
- **asyncpg:** no JSONB codec. Read JSONB as text and `json.loads` it. Write with `json.dumps(...)` and a `::jsonb` cast.
- **Web:** standalone components with signals, Transloco strings in both `en.json` and `bn.json` (same keys), `--shopper-*` tokens and the shared classes in `src/styles.scss`. Component styles stay under 2 kB where possible (4 kB fails the build). Check new pages at 360 px in Bangla.
- **Line endings:** `.gitattributes` stores text as LF. Do not rewrite whole files to change line endings.
- **Money:** `Decimal` in Python, strings with 2 decimals over the wire from mobile.

## Decisions applied in this plan

The user confirmed D2, D3, D4 and D6 on 2026-11-13. D1 and D5 are defaults. If the user changes one, edit the sessions listed next to it before running them.

| ID | Decision | Sessions |
|---|---|---|
| D1 | The Admin link leaves the staff nav. The platform admin opens `/admin/tenants` directly with the platform API key. | B2 |
| D2 | Account transfers and supplier payments need accountant, manager or admin. Expenses stay open to all staff. Staff create stays admin only. | A3 |
| D3 | `module_access` only hides web nav links and routes. A missing key means the module is on. The API does not enforce modules (deferred X3). | B2 |
| D4 | Theme: the user's own saved choice wins. The tenant theme applies only when the user has not picked one. | B1 |
| D5 | Per-branch FIFO costing is deferred (X2). The QR link expiry stays an app setting (closed, no work). | none |
| D6 | Mobile login takes a shop code (tenant subdomain), username and password. | E1, E2 |

## Tracker

Status values: `todo`, `doing`, `done`, `blocked`. Fill `Result` with date and test counts.

| ID | Session | Needs | Status | Result |
|---|---|---|---|---|
| P0 | Commit pending work, LF line endings, sync docs and agent memory | none | done | 2026-11-13: API 318/19, ng build ok |
| A1 | API: tenant settings readable by all staff | none | done | 2026-11-22: API 320/19 |
| A2 | API+web: gateway return and IPN URLs | none | done | 2026-11-22: API 330/19, web 64 passed, ng build ok |
| A3 | API: typed bodies and roles for money and staff endpoints | none | done | 2026-11-22: API 354/19; no web form posts these routes, so no web change |
| A4 | API: make test_pos_e2e run against the scratch DB | none | done | 2026-11-27: integration 18 passed, 0 skipped; unit 364/25. The test found that every stock-in movement failed on a real DB since 013: the BEFORE INSERT trigger added a cost_layers row before its stock_transactions row existed (FK violation, old one-column FK too). Fixed by new migration 033_cost_layer_after_insert.sql (cost layer and WAC now AFTER INSERT; 'out' stays BEFORE) with test_migration_033.py; applied twice on shopper_verify. F2 moves to migration 034 |
| B1 | Web: tenant settings store, theme and language after login | A1 | done | 2026-11-22: web 78 passed, ng build ok |
| B2 | Web: nav by role and module, module guard, module switches | B1 | done | 2026-11-22: web 89 passed, ng build ok |
| B3 | Web: warn before leaving /settings with unsaved changes | none | done | 2026-11-22: web 93 passed, ng build ok |
| B4 | Web: translate home, accounting, customers, expenses | none | done | 2026-11-22: web 96 passed, ng build ok. Shared data grid now pipes `label` through transloco; page headers wrap at 360 px |
| B5 | Web: translate inventory, invoices, procurement, staff, suppliers | B4 | done | 2026-11-22: web 97 passed, ng build ok. Also checkout gateway labels; added missing `suppliers.addTitle`; invoice cancel prompt and error fallback go through TranslocoService |
| B6 | Web: Playwright checks (settings 360 px Bangla) and page look-over | B2, B3, B5 | done | 2026-11-22: e2e 37 passed, twice in a row (`npm run e2e`, all API calls stubbed, so no DB). Stable enough for G1 to add to CI. Web 97 passed, ng build ok. Fixed 360 px overflow on home, procurement tabs, suppliers with wrap/padding classes. Note: settings-page.component.scss is 2.9 kB, over the 2 kB soft limit (4 kB fails the build). Left as is by choice. If it grows, move the receipt preview into its own component and .savebar into styles.scss. |
| B7 | Web: Bangla letter-spacing and pale tints | B6 | done | 2026-11-22: web 97 passed, build clean, e2e 37 passed (each Bangla page now also fails on letter-spacing). Letter-spacing is off under `[lang\|=bn]`, not `:lang(bn)`: the build's CSS optimizer drops `:lang`. All `text-slate-300/400/500` now `text-shopper-muted` (new Tailwind color from `--shopper-muted`). Found in B6 look-over. `tracking-widest` and `tracking-[0.2em]` split Bangla letters (data grid headers, stat labels on 9 pages); turn letter-spacing off under `:lang(bn)` in styles.scss. Grid empty text `text-slate-300` is too pale; move hard-coded `slate-*` text to a `--shopper-*` muted token. Check with `E2E_SHOTS=1 npm run e2e`. |
| C1 | DB: migration 032, tenant-qualified foreign keys | none | done | 2026-11-27: API 360/19. The 35 links match every one-column FK in shopper_verify. Precheck takes po_lines' tenant from its purchase order, since po_lines has no tenant_id before 032 |
| C2 | DB: apply 032 on scratch, cross-tenant FK integration tests | C1 | done | 2026-11-27: precheck all 0; 032 applied and rerun on shopper_verify (35 `_tfk` FKs). Integration 17 passed, 1 skipped (test_pos_e2e, A4); unit 360/25 (new file skips without DB). Applied with asyncpg as postgres: psql is not on PATH, and shopper_verify has no platform.schema_migrations table |
| D1 | Tests: DB-backed product, invoice, return and refund flows | A4, C2 | done | 2026-11-27: integration 24 passed, 0 skipped; unit 365/31 (the new tests skip without the integration env). Review of 033 found that stock with no cost layers sold at cost 0; user chose to fix it in 033: `cost_layers.transaction_id` is now nullable and each product with stock and no layers gets one layer at its WAC or buy price (sixth test covers it). Not fixed: damage, expired, gift_out, return_out and transfer movements never touch cost layers (same as 013). Also `core/db.py` now sets the pools to None on shutdown, so a later test in the same run does not pick up a closed pool. |
| D2 | Tests: marketplace search and suspended tenant on a real DB | A4 | done | 2026-11-27: integration 28 passed, 0 skipped; unit 365/35 (the 4 new tests skip without the integration env). Suspended, canceled and pending shops also drop out of marketplace search. Found: `search_public_marketplace_products` (026) lists only `active` shops, so trialing and past_due shops can sell but are not in the marketplace. User chose to list them: session D3 |
| D3 | DB: marketplace search lists trialing and past_due shops (migration 035) | D2 | done | 2026-11-27: 035 applied twice on shopper_verify; integration 28 passed, 0 skipped (the trialing/past_due test now also checks marketplace search; the blocked-status test now also covers `deleted`); unit 369 passed / 35 skipped (+4 in test_migration_035.py) |
| E1 | Mobile: API URL, shop code and request headers | none | todo | |
| E2 | Mobile: login matches the API | E1 | todo | |
| E3 | Mobile: products from /pos/sync, remove dead calls | E1 | todo | |
| E4 | Contract check: openapi.json and a mobile path test | E2, E3 | todo | |
| F1 | Web: branches screen | B2 | todo | |
| F2 | DB+API: branch on invoices and POS sales (migration 034) | C2, D1 | todo | |
| G1 | CI: run on dev2, add web unit tests and Flutter | none | todo | |
| G2 | Repo: remove one-off scripts, mark old docs historical | none | todo | |
| G3 | Docs close-out (README, DEPLOY, ARCHITECTURE_MAP, spec, tasks) | all above except blocked | todo | |

Order when one person works alone: A1, A2, A3, B1, B2, B3, B4, B5, C1, C2, A4, D1, D2, D3, E1, E2, E3, E4, B6, F1, F2, G1, G2, G3.

Blocked on outside input (not in the tracker; see "Blocked and deferred"): X1 gateway contracts, X4 live deploy checks.

---

## P0. Commit pending work, sync docs and agent memory (done 2026-11-13)

Done in the session that wrote this plan:
- Committed the 2026-11-06 work (storefront URLs, web settings follow-ups, RLS test cleanup) after rerunning the API suite (318 passed, 19 skipped) and `ng build`.
- `.gitattributes`: `* text=auto eol=lf`, CRLF for `.bat/.cmd/.ps1`, binaries marked. Closes the "add .gitattributes" item.
- `.gitignore`: Playwright screenshots and logs, `.angular/`.
- Verified done, no work: "no theme switch under 1024 px except /settings". The header theme dots are `hidden lg:flex` (app.component.html), and /settings has its own theme picker.
- AGENTS.md and CLAUDE.md added for all agents; tasks.md, plan.md, spec.md, README and the plans README point here; tasks.md maps every open item to a session.
- Historical banner added to `docs/Shopper-Refactor-Plan.md` and `docs/COMPREHENSIVE_ARCHITECTURE_SECURITY_REVIEW.md`.

---

## A1. API: tenant settings readable by all staff

**Why:** `GET /v1/tenant/settings` needs a manager, so a cashier's web app never gets the shop's theme, language or modules (B1, B2 need it). The response has no secrets: gateway credentials are only in `TenantSettingsInternalOut`.

**Files:** `apps/api/routers/settings.py`, `apps/api/tests/api/test_api_smoke.py` (or a new `tests/unit/test_settings_roles.py`).

**Steps**
1. In `routers/settings.py`, import `StaffDep` and change `get_tenant_settings(..., _auth: ManagerDep, ...)` to `_auth: StaffDep`. Leave `update_tenant_settings` on `ManagerDep`. In `update_tenant_settings`, the no-change path calls `get_tenant_settings(ctx, _auth, settings)`; keep it.
2. New file `tests/unit/test_settings_roles.py`:
   ```python
   def test_cashier_can_read_settings(client, staff_token_headers):
       assert client.get("/v1/tenant/settings", headers=staff_token_headers).status_code == 200

   def test_cashier_cannot_change_settings(client, staff_token_headers):
       r = client.patch("/v1/tenant/settings", json={"theme_id": "ruby"}, headers=staff_token_headers)
       assert r.status_code == 403
   ```

**Acceptance:** cashier GET 200, cashier PATCH 403, manager PATCH unchanged (existing tests pass).
**Verify:** API unit suite: 320 passed, 19 skipped.

---

## A2. API+web: gateway return and IPN URLs

**Bugs fixed:**
- `ipn_url` is built from `PLATFORM_ROOT_DOMAIN`, which is a bare domain used for Host matching (`shopper.com`). The result has no scheme, no tenant and no `/api` prefix, so SSLCommerz cannot reach it.
- `success_url`, `fail_url`, `cancel_url` point at `/checkout/success|fail|cancel` on the web app. SSLCommerz sends a **POST** there, which the static web server refuses, and the web route `/checkout/:id` would read `success` as an invoice id.

**Files:** `apps/api/services/payment_gateway.py`, `apps/api/routers/storefront.py`, new `apps/api/tests/unit/test_checkout_return.py`, `apps/shopper-web/src/app/app.routes.ts`, new `apps/shopper-web/src/app/features/checkout/checkout-result.component.ts` (+ `.spec.ts`), `en.json`, `bn.json`.

**Steps**
1. `routers/storefront.py` (prefix `/v1/storefront`), add:
   ```python
   from typing import Literal
   from fastapi.responses import RedirectResponse

   @router.api_route("/checkout/return/{result}", methods=["GET", "POST"], include_in_schema=False)
   async def checkout_return(result: Literal["success", "fail", "cancel"]):
       # Gateways POST here; the browser then loads the web page on the same host.
       return RedirectResponse(url=f"/checkout/result?status={result}", status_code=303)
   ```
2. `services/payment_gateway.py`, in `SSLCommerzGateway.initiate_payment`: delete the `api_base = ...` line and build:
   ```python
   api_url_base = f"{storefront_url}/api"  # openresty strips /api and forwards to the API
   ipn_url = f"{api_url_base}/v1/tenant/payments/ipn/sslcommerz?tenant={tenant_subdomain}"
   return_base = f"{api_url_base}/v1/storefront/checkout/return"
   ```
   and set `success_url`, `fail_url`, `cancel_url` to `f"{return_base}/success"`, `/fail`, `/cancel`.
3. `git grep -n "checkout/success\|api.shopper.com\|ipn_url" apps/api` and update any test assertion to the new URLs.
4. Test file `test_checkout_return.py`:
   - POST and GET `/v1/storefront/checkout/return/success` with `X-Shopper-Tenant: demo`, `follow_redirects=False` → 303, `location == "/checkout/result?status=success"`.
   - `/checkout/return/other` → 422.
   - Call `SSLCommerzGateway().initiate_payment` with `httpx.AsyncClient.post` monkeypatched to capture `data`, settings `storefront_public_base_url="https://shop.example"`, subdomain `acme`: assert `ipn_url == "https://acme.shop.example/api/v1/tenant/payments/ipn/sslcommerz?tenant=acme"` and `success_url == "https://acme.shop.example/api/v1/storefront/checkout/return/success"`. Build `TenantSettingsInternalOut` the same way existing payment tests do (`git grep -n "TenantSettingsInternalOut(" apps/api/tests`).
5. Web: in `app.routes.ts` add `{ path: 'checkout/result', component: CheckoutResultComponent }` **above** `checkout/:id`. The component reads `status` from the query string and shows `checkout.result.success|fail|cancel`, or `checkout.result.unknown` for anything else, plus a short line that the shop will see the payment once the gateway confirms it. No guard, no API call.
6. Strings (en / bn): `checkout.result.success` "Payment received. You can close this page." / "পেমেন্ট পাওয়া গেছে। এই পাতা বন্ধ করতে পারেন।", `fail` "The payment did not go through. Nothing was charged." / "পেমেন্ট হয়নি। কোনো টাকা কাটা হয়নি।", `cancel` "You cancelled the payment." / "আপনি পেমেন্ট বাতিল করেছেন।", `unknown` "We could not read the payment result." / "পেমেন্টের ফল পড়া যায়নি।", `pending` "The shop will see the payment once the gateway confirms it." / "গেটওয়ে নিশ্চিত করলে দোকান পেমেন্টটি দেখতে পাবে।".
7. Spec: the component shows the success text for `?status=success` and the unknown text for `?status=x`.

**Acceptance:** gateway URLs reach the API through the tenant host; a POST from the gateway lands the customer on `/checkout/result`; bKash and Nagad still fail closed (no change there).
**Verify:** API suite (+4 or more tests), web tests and build. Note for G3: DEPLOY must say that `STOREFRONT_PUBLIC_BASE_URL` must be host style (no path), because openresty serves `/api/` only at the root of the host.

---

## A3. API: typed bodies and roles for money and staff endpoints

**Bugs fixed:** `POST /accounts/transfer`, `POST /expenses` and `POST /staff` take `body: dict`. Bad input gives 500 (`Decimal("abc")`, `pwd_context.hash(None)`, a bad role hits the enum, a duplicate username hits the unique key). Any cashier can move money between accounts and record supplier payments.

**Files:** `apps/api/schemas/common.py` (or a new `schemas/admin_ops.py`, exported from `schemas/__init__.py`), `routers/accounts.py`, `routers/expenses.py`, `routers/staff.py`, `routers/procurement.py`, new `tests/unit/test_typed_bodies.py`.

**Steps**
1. Schemas:
   ```python
   class AccountTransferCreate(BaseModel):
       from_account_code: str = Field(min_length=1, max_length=50)
       to_account_code: str = Field(min_length=1, max_length=50)
       amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
       description: str | None = Field(default=None, max_length=500)

       @model_validator(mode="after")
       def _different(self):
           if self.from_account_code == self.to_account_code:
               raise ValueError("from and to accounts must differ")
           return self

   class ExpenseCreate(BaseModel):
       category_id: UUID
       amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
       description: str | None = Field(default=None, max_length=500)

   class StaffCreate(BaseModel):
       username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
       password: str = Field(min_length=8, max_length=128)
       full_name: str | None = Field(default=None, max_length=120)
       role: Literal["cashier", "accountant", "manager", "admin"] = "cashier"
       branch_id: UUID | None = None
   ```
2. Routers: replace `body: dict` with the schema and `body.get("x")` with `body.x`. Keep the response shapes.
   - accounts `transfer_funds`: `auth: AccountantDep` (D2).
   - procurement `record_supplier_payment`: `_auth: AccountantDep` (D2).
   - staff `create_staff`: keep the admin check. Wrap the insert in `try/except asyncpg.UniqueViolationError` → `HTTPException(409, "Username already exists")`. Remove the manual `UUID(str(...))` parse (the schema does it).
3. Web: the accounting page has a transfer form? `git grep -n "transfer" apps/shopper-web/src/app/features/accounting`. If it posts a transfer, hide the form unless `auth.role()` is `accountant`, `manager` or `admin`. Same for the supplier payment form in procurement.
4. Tests (`test_typed_bodies.py`, call the route functions with fake ctx/conn like `test_staff_branch.py` does, or use `client` with tokens):
   - transfer amount `"abc"` → 422, same accounts → 422, cashier → 403, accountant passes validation.
   - expense with non-UUID category → 422.
   - staff create without password → 422, role `owner` → 422, duplicate username → 409.
   - supplier payment as cashier → 403.

**Acceptance:** no 500 for bad bodies on these routes; D2 roles enforced; existing tests pass after updating any that posted dicts.
**Verify:** API suite and web tests/build.

---

## A4. API: make test_pos_e2e run against the scratch DB

**Bug:** `tests/conftest.py` sets `TESTING=1` at import, and `test_pos_e2e.py` skips when `TESTING == "1"`. So it can never run. It also expects a seeded `demo` tenant with `admin/password`.

**Files:** `apps/api/tests/integration/test_pos_e2e.py`, new `apps/api/tests/integration/seed.py`.

**Steps**
1. `seed.py`: `async def seed_demo(migrate_dsn) -> dict` that, as the migrate role, creates tenant `e2e<6 hex>` (status `active`), its `platform.tenant_settings` row, a main branch (`is_main = true`), and a staff `admin` with role `admin` and password `password-e2e` hashed with `passlib` bcrypt (same `pwd_context` as `routers/auth.py`). Return ids and the subdomain. Add `async def drop_tenant(migrate_dsn, tenant_id)` using the same cleanup order as `_cleanup_tenant_data` in `test_rls_isolation.py`, extended with every `tenant_data` table the flow writes (find them with `SELECT table_name FROM information_schema.columns WHERE table_schema='tenant_data' AND column_name='tenant_id'`, delete children before parents, `audit_log` last).
2. `test_pos_e2e.py`:
   - Skip unless `INTEGRATION_TEST=1` and both DSNs are set (same rule as `test_rls_isolation.py`).
   - In the test: `monkeypatch.setenv("TESTING", "0")`, `monkeypatch.setenv("ALLOW_TENANT_OVERRIDE", "true")`, call `clear_settings_cache()`, then `async with app.router.lifespan_context(app):` and `AsyncClient(transport=ASGITransport(app=app), base_url=f"http://{sub}.localhost")`.
   - Keep the flow: login, create product with stock, POS offline-punch one sale, check stock and invoice balance. Fix field names to the current schemas if they fail.
   - `finally:` drop the tenant.

**Acceptance:** with integration env set, `tests/integration` runs 12 passed, 0 skipped; without it, the unit suite is unchanged (318 passed, 19 skipped, or the new count after earlier sessions).
**Verify:** both API commands.

---

## B1. Web: tenant settings store, theme and language after login

**Bugs fixed:** `tenant-bootstrap.ts` runs at app start, before login, and only managers could read settings. So the tenant theme and language are almost never applied. When it does run it sets `data-theme` directly, bypassing `ThemeService`, so the header shows the wrong current theme. `ThemeService` reads `localStorage` without a guard and trusts any saved string.

**Files:** new `src/app/core/tenant/tenant-settings.store.ts` (+ spec), `core/tenant/tenant-bootstrap.ts`, `core/theme/theme.service.ts` (+ spec), `features/login/login-page.component.ts`, `app.component.ts`, `app.config.ts`.

**Steps**
1. `ThemeService`:
   - Export `SHOPPER_THEMES` (the 12 ids) and `isShopperTheme(x): x is ShopperTheme`.
   - `hasSavedTheme(): boolean` (true when storage holds a valid id).
   - Constructor: read storage in try/catch, apply only a valid id.
   - `setTheme(t, opts = { persist: true })`: when `persist` is false, apply and set the signal but do not write storage.
2. `TenantSettingsStore` (`providedIn: 'root'`): signal `settings = signal<TenantSettingsDto | null>(null)`; `load(): Promise<void>` calls `TenantSettingsService.load()`, on success sets the signal and applies:
   - theme: if `!theme.hasSavedTheme() && isShopperTheme(s.theme_id)` → `theme.setTheme(s.theme_id, { persist: false })` (D4).
   - language: if no `shopper.lang` in storage → `locale.setLanguage(lang, { persist: false })` (same as today).
   - on error: leave the signal null, apply nothing.
   `clear()` sets null. `moduleOn(key)` returns `settings()?.module_access?.[key] !== false` (D3).
3. `tenant-bootstrap.ts`: only call `store.load()` when `auth.isLoggedIn()`. Delete the direct `setAttribute`.
4. Login page: after a successful login call `store.load()` before navigating. `AppComponent.logout()`: call `store.clear()`.
5. Settings page save: after `this.theme.setTheme(...)` also `store.settings.set(s)`.
6. Specs: store applies the tenant theme when nothing is saved; keeps the saved theme otherwise; does nothing on error; bootstrap does not call the API when logged out.

**Acceptance:** a cashier who logs in gets the shop's theme and language unless they picked their own; header dots show the active theme; logged-out start makes no settings call.
**Verify:** web tests and build.

---

## B2. Web: nav by role and module, module guard, module switches

**Bugs fixed:** every nav link shows to everyone; Admin (platform) shows to shop staff; with `module_access = {}` (what seeds and registration create) the settings page shows no module switches at all.

**Files:** new `src/app/core/nav/nav-items.ts` (+ spec), new `core/nav/module.guard.ts`, `app.component.ts`, `app.component.html`, `app.routes.ts`, `features/settings/settings-page.component.ts` and `.html`, `en.json`, `bn.json`.

**Steps**
1. `nav-items.ts`:
   ```ts
   export type StaffRole = 'cashier' | 'accountant' | 'manager' | 'admin';
   export const MODULE_KEYS = ['inventory', 'procurement', 'expenses', 'accounting', 'customers', 'pos'] as const;
   export interface NavItem { path: string; label: string; roles?: StaffRole[]; module?: typeof MODULE_KEYS[number]; exact?: boolean }
   export const NAV_ITEMS: NavItem[] = [
     { path: '/', label: 'nav.home', exact: true },
     { path: '/products', label: 'nav.products' },
     { path: '/invoices', label: 'nav.invoices' },
     { path: '/inventory', label: 'nav.inventory', module: 'inventory' },
     { path: '/procurement', label: 'nav.procurement', module: 'procurement' },
     { path: '/suppliers', label: 'nav.suppliers', module: 'procurement' },
     { path: '/expenses', label: 'nav.expenses', module: 'expenses' },
     { path: '/payments', label: 'nav.payments', roles: ['manager', 'admin'] },
     { path: '/accounting', label: 'nav.accounting', module: 'accounting' },
     { path: '/customers', label: 'nav.customers', module: 'customers' },
     { path: '/staff', label: 'nav.staff' },
     { path: '/branches', label: 'nav.branches', roles: ['admin'] },   // added by F1; leave out until F1
     { path: '/settings', label: 'nav.settings', roles: ['manager', 'admin'] },
   ];
   export function visibleNav(role: string | null, moduleOn: (k: string) => boolean): NavItem[]
   ```
   Roles follow the API: payments review and settings edit need a manager. `pos` has no web page (mobile only).
2. `app.component.html`: render the nav with `@for (item of nav(); track item.path)` where `nav = computed(() => visibleNav(auth.role(), k => store.moduleOn(k)))`. Remove the Admin link (D1). Make `auth` public or expose `role`.
3. `module.guard.ts`: `moduleGuard(key)` returns true when `store.moduleOn(key)`, else `createUrlTree(['/'])`. Add `canActivate: [moduleGuard('inventory')]` etc. to the routes that have a module. Add `roleGuard(['manager','admin'])` on `payments` and `settings`. Guards allow the route when settings are not loaded yet (store null) so a slow API never locks pages; the API still checks roles.
4. Settings page: build the switch list from `MODULE_KEYS` merged with any extra keys in `module_access`. A missing key shows as on. Save sends the full map only when something changed (keep "send only changed fields"). Translate every key: `settings.moduleNames.inventory|procurement|expenses|accounting|customers|pos` (en: Inventory, Purchasing and suppliers, Expenses, Accounting, Customers, Mobile POS; bn: ইনভেন্টরি, ক্রয় ও সরবরাহকারী, খরচ, হিসাব, গ্রাহক, মোবাইল পিওএস). Remove `NAMED_MODULES`.
5. Specs: `visibleNav` for cashier hides payments and settings; module `inventory: false` hides Inventory; admin sees settings; guard redirects when the module is off; settings page shows six switches for `module_access = {}`.

**Acceptance:** as listed; no route is removed; `/admin/tenants` still opens by URL.
**Verify:** web tests and build.

---

## B3. Web: warn before leaving /settings with unsaved changes

**Files:** new `src/app/core/nav/unsaved-changes.guard.ts` (+ spec), `app.routes.ts`, `features/settings/settings-page.component.ts`, `en.json`, `bn.json`.

**Steps**
1. `export interface HasUnsavedChanges { hasUnsavedChanges(): boolean }` and `unsavedChangesGuard: CanDeactivateFn<HasUnsavedChanges> = (c) => !c.hasUnsavedChanges() || window.confirm(translate('settings.leaveUnsaved'))` (use `TranslocoService.translate`).
2. Settings page implements it with the same diff it uses to build the PATCH body (empty diff = no changes). Also add `@HostListener('window:beforeunload', ['$event'])` that calls `event.preventDefault()` when there are changes.
3. Route: `{ path: 'settings', ..., canDeactivate: [unsavedChangesGuard] }`.
4. Strings: `settings.leaveUnsaved` en "You have unsaved changes. Leave this page?" bn "সেভ না করা পরিবর্তন আছে। পাতা ছেড়ে যাবেন?"
5. Spec: guard returns true with no changes, asks `confirm` with changes (spy returns false → false).

**Verify:** web tests and build.

---

## B4. Web: translate home, accounting, customers, expenses

Hard-coded English found on 2026-11-13 (rough count of visible strings): home 6, accounting 8, customers 6, expenses 7.

**Files:** the four feature files plus `en.json`, `bn.json`.

**Steps**
1. For each file, replace every visible English string (headings, labels, buttons, table headers, empty states, placeholders, error text) with a Transloco key under the page's namespace: `home.*`, `accounting.*`, `customers.*`, `expenses.*`. Table column definitions with `label: 'X'` become `label: 'customers.cols.x'` and the template pipes them through `transloco`.
2. Add every key to both JSON files. Bangla must be real Bangla, not English.
3. Check with: `git grep -nE ">[A-Z][a-z]+[ a-zA-Z,.]*<|label: '[A-Z]|placeholder=\"[A-Z]" -- <the four files>` → no hits.
4. Add a key-parity test `src/app/core/i18n/i18n-keys.spec.ts` that flattens both JSON files and expects the same key set.

**Verify:** web tests (+1 spec) and build.

---

## B5. Web: translate inventory, invoices, procurement, staff, suppliers

Same method as B4 for: inventory 9, invoices 7, procurement 17, staff 6, suppliers 6 strings, plus the 2 left in checkout. Namespaces `inventory.*`, `invoices.*`, `procurement.*`, `staff.*`, `suppliers.*`, `checkout.*`. The grep check and the key-parity test from B4 must pass.

**Verify:** web tests and build.

---

## B6. Web: Playwright checks and page look-over

**Files:** `apps/shopper-web/package.json` (devDependency `@playwright/test`, script `"e2e": "playwright test"`), new `apps/shopper-web/playwright.config.ts`, new `apps/shopper-web/e2e/fixtures.ts`, new `apps/shopper-web/e2e/layout.spec.ts`, `.gitignore` (`apps/shopper-web/test-results/`, `apps/shopper-web/playwright-report/`).

**Steps**
1. Config: `webServer: { command: 'npx ng serve --port 4300', url: 'http://localhost:4300', reuseExistingServer: true }`, `use.baseURL`, one Chromium project.
2. `fixtures.ts`: a test fixture that puts a fake JWT in `sessionStorage['shopper.token']` (payload `{role:'manager', exp: now+3600}`), sets `localStorage['shopper.lang']='bn'`, and stubs `**/api/v1/tenant/**` with `page.route`: settings returns the DTO from `settings-page.component.spec.ts`; every list endpoint returns `[]`.
3. `layout.spec.ts`: for each width 360, 390, 1440 and each route in `NAV_ITEMS` plus `/settings`: open it, wait for `main`, assert `document.documentElement.scrollWidth <= window.innerWidth`. For `/settings` at 360 px also change one field and assert the PATCH body has only that field.
4. Look-over: run it once with `--headed` or screenshots, look at each page for unreadable tints or hover colours turned on by the Tailwind colour fix (2026-11-06). Fix only colour classes and spacing in the page files. List anything bigger as a new row in the Tracker.
5. G1 adds this to CI only if it is stable in two runs in a row; otherwise it stays a local check (write that in the row).

**Acceptance:** no sideways scroll on any page at 360 px in Bangla.
**Verify:** `npx playwright install chromium && npm run e2e`, web tests and build.

---

## C1. DB: migration 032, tenant-qualified foreign keys

**Bug:** foreign key checks ignore RLS. A tenant who knows another tenant's row id can point at it (for example an expense in another tenant's category). Only 4 links were tenant-qualified (invoice lines, payments, settlements, product category). `po_lines` has no `tenant_id` at all.

**Files:** new `database/migrations/032_tenant_fks.sql`, new `apps/api/tests/unit/test_migration_032.py`, new `database/checks/032_precheck.sql`.

**Precheck (`database/checks/032_precheck.sql`)**: one `SELECT` per link in the table below that counts child rows whose parent has a different `tenant_id`, for example
`SELECT 'expenses.category_id', count(*) FROM tenant_data.expenses c JOIN tenant_data.expense_categories p ON p.id = c.category_id WHERE p.tenant_id <> c.tenant_id`, joined with `UNION ALL`. Every count must be 0 before 032 runs on a real DB. Run as the migrate role.

**Migration**
```sql
-- database/migrations/032_tenant_fks.sql
-- Foreign keys check tenant_id too, so a row can only point at a row of its own tenant
-- (FK checks bypass RLS). po_lines gets tenant_id. One FK per link; delete rules unchanged.
-- Safe to rerun.

BEGIN;

ALTER TABLE tenant_data.po_lines ADD COLUMN IF NOT EXISTS tenant_id UUID;
UPDATE tenant_data.po_lines l SET tenant_id = po.tenant_id
  FROM tenant_data.purchase_orders po
 WHERE po.id = l.po_id AND l.tenant_id IS NULL;
ALTER TABLE tenant_data.po_lines ALTER COLUMN tenant_id SET DEFAULT tenant_data.app_tenant_id();
ALTER TABLE tenant_data.po_lines ALTER COLUMN tenant_id SET NOT NULL;
DROP POLICY IF EXISTS tenant_isolation_po_lines ON tenant_data.po_lines;
CREATE POLICY tenant_isolation_po_lines ON tenant_data.po_lines FOR ALL TO shopper_app
  USING (tenant_id = tenant_data.app_tenant_id())
  WITH CHECK (tenant_id = tenant_data.app_tenant_id());

DO $$
DECLARE
  r record;
  c record;
  fk text;
BEGIN
  FOR r IN SELECT * FROM (VALUES
    ('product_categories',  'parent_id',       'product_categories', 'SET NULL'),
    ('products',            'category_id',     'product_categories', 'SET NULL'),
    ('stock_transactions',  'product_id',      'products',           'CASCADE'),
    ('stock_transactions',  'branch_id',       'branches',           'NO ACTION'),
    ('invoices',            'customer_id',     'customers',          'SET NULL'),
    ('invoice_lines',       'invoice_id',      'invoices',           'CASCADE'),
    ('invoice_lines',       'product_id',      'products',           'SET NULL'),
    ('payments',            'invoice_id',      'invoices',           'SET NULL'),
    ('cost_layers',         'product_id',      'products',           'CASCADE'),
    ('cost_layers',         'transaction_id',  'stock_transactions', 'CASCADE'),
    ('purchase_orders',     'supplier_id',     'suppliers',          'NO ACTION'),
    ('po_lines',            'po_id',           'purchase_orders',    'CASCADE'),
    ('po_lines',            'product_id',      'products',           'NO ACTION'),
    ('expenses',            'category_id',     'expense_categories', 'NO ACTION'),
    ('expenses',            'staff_id',        'staff',              'NO ACTION'),
    ('customer_collections','customer_id',     'customers',          'NO ACTION'),
    ('customer_collections','collected_by',    'staff',              'NO ACTION'),
    ('account_transfers',   'from_account_id', 'accounts',           'NO ACTION'),
    ('account_transfers',   'to_account_id',   'accounts',           'NO ACTION'),
    ('account_transfers',   'staff_id',        'staff',              'NO ACTION'),
    ('credit_notes',        'invoice_id',      'invoices',           'CASCADE'),
    ('debit_notes',         'supplier_id',     'suppliers',          'NO ACTION'),
    ('debit_notes',         'po_id',           'purchase_orders',    'NO ACTION'),
    ('supplier_payments',   'supplier_id',     'suppliers',          'NO ACTION'),
    ('supplier_payments',   'po_id',           'purchase_orders',    'NO ACTION'),
    ('credit_note_lines',   'credit_note_id',  'credit_notes',       'CASCADE'),
    ('credit_note_lines',   'invoice_id',      'invoices',           'CASCADE'),
    ('credit_note_lines',   'invoice_line_id', 'invoice_lines',      'CASCADE'),
    ('credit_note_lines',   'product_id',      'products',           'RESTRICT'),
    ('stock_levels',        'branch_id',       'branches',           'NO ACTION'),
    ('stock_levels',        'product_id',      'products',           'CASCADE'),
    ('staff',               'branch_id',       'branches',           'NO ACTION'),
    ('payment_refunds',     'payment_id',      'payments',           'NO ACTION'),
    ('payment_refunds',     'invoice_id',      'invoices',           'NO ACTION'),
    ('payment_refunds',     'credit_note_id',  'credit_notes',       'NO ACTION')
  ) AS t(child, col, parent, on_delete)
  LOOP
    -- The parent needs a unique key on (tenant_id, id).
    IF NOT EXISTS (
      SELECT 1 FROM pg_index i
       WHERE i.indrelid = format('tenant_data.%I', r.parent)::regclass
         AND i.indisunique
         AND pg_get_indexdef(i.indexrelid) LIKE '%(tenant_id, id)'
    ) THEN
      EXECUTE format('CREATE UNIQUE INDEX %I ON tenant_data.%I (tenant_id, id)',
                     'uq_' || r.parent || '_tenant_id_id', r.parent);
    END IF;

    -- Drop every FK on this column (the old one-column FK, or an earlier tenant FK).
    FOR c IN
      SELECT con.conname
        FROM pg_constraint con
        JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey)
       WHERE con.conrelid = format('tenant_data.%I', r.child)::regclass
         AND con.contype = 'f'
         AND a.attname = r.col
    LOOP
      EXECUTE format('ALTER TABLE tenant_data.%I DROP CONSTRAINT %I', r.child, c.conname);
    END LOOP;

    fk := r.child || '_' || r.col || '_tfk';
    EXECUTE format(
      'ALTER TABLE tenant_data.%I ADD CONSTRAINT %I FOREIGN KEY (tenant_id, %I) '
      'REFERENCES tenant_data.%I (tenant_id, id) ON DELETE %s NOT VALID',
      r.child, fk, r.col, r.parent,
      CASE WHEN r.on_delete = 'SET NULL' THEN format('SET NULL (%I)', r.col) ELSE r.on_delete END);
    EXECUTE format('ALTER TABLE tenant_data.%I VALIDATE CONSTRAINT %I', r.child, fk);
  END LOOP;
END $$;

COMMIT;
```
Notes for the executor:
- `ON DELETE SET NULL (col)` needs PostgreSQL 15 or later. docker-compose uses 16, local is 18.2. Without the column list, a parent delete would also null `tenant_id` and fail.
- The old composite FKs from 025/026 (`invoice_lines_invoice_tenant_fk`, `payments_invoice_tenant_fk`, `products_category_tenant_fk`) used NO ACTION while the one-column FK used CASCADE or SET NULL. The loop replaces both with one FK that keeps the one-column rule. `invoice_settlements` already has a correct composite FK and is not in the list.
- `init/01_schema_rls.sql` is not changed; 032 runs after it on a fresh DB.
- `procurement.py` inserts `po_lines` without `tenant_id`; the column default fills it from the request's tenant. No code change.

**Static test (`test_migration_032.py`)**: one transaction; every pair in the VALUES list appears; `SET NULL (%I)` is used for SET NULL; `po_lines` gets `tenant_id`, default, NOT NULL and the new policy with `WITH CHECK`; the precheck file has one SELECT per link (count of `UNION ALL` = links − 1).

**Verify:** API unit suite (+5 or so tests).

---

## C2. DB: apply 032 on scratch, cross-tenant FK integration tests

**Files:** new `apps/api/tests/integration/test_tenant_fks.py`.

**Steps**
1. Run `database/checks/032_precheck.sql` on `shopper_verify` → all zeros.
2. Apply migrations on `shopper_verify`, then run 032 a second time → no error.
3. Test file (same env and fixtures style as `test_rls_isolation.py`; seed two tenants A and B with the migrate DSN):
   - As shopper_app with tenant A set, insert an expense pointing at tenant B's expense category → `asyncpg.ForeignKeyViolationError`.
   - Same for `invoice_lines.product_id` → B's product, and `stock_levels.branch_id` → B's branch.
   - Delete a product category in A that a product uses → succeeds and the product's `category_id` is NULL, `tenant_id` unchanged.
   - Delete an invoice in A (migrate role) → its `invoice_lines` are gone, its `payments.invoice_id` is NULL.
   - Clean up both tenants.
4. Run the whole integration folder.

**Acceptance:** cross-tenant references fail; delete rules behave as before; all earlier integration tests pass.
**Verify:** API unit and integration suites.

---

## D1. Tests: DB-backed product, invoice, return and refund flows

Closes "Run database-backed integration tests for product, invoice, return, and POS flows".

**Files:** new `apps/api/tests/integration/test_commerce_flows.py` (uses `seed.py` from A4 and the same lifespan/AsyncClient setup).

**Cases** (each its own test, own seeded tenant, cleanup in `finally`):
1. Product create with `stock_quantity` 10 → `stock_levels` for the main branch is 10, `products.stock_quantity` is 10, one `stock_transactions` row with `reason_code = 'opening'`.
2. Invoice draft → issue → stock drops by the line qty, Mushak 6.3 lines exist, status `issued`. Cancel → stock back, reversing VAT lines, status `cancelled`.
3. Issue with qty above stock → 409, nothing changed.
4. Sales return of part of a line → credit note with form 6.7 negative VAT lines, stock back, a second return above the unreturned balance → 4xx.
5. Gateway-free refund: insert a completed payment with the migrate role, POST a refund as manager → invoice balance goes back up; two refunds above the payment amount → 409.

Use the exact routes from the API (`/v1/tenant/invoices`, `/{id}/issue`, `/{id}/cancel`, `/invoices/returns`, `/payments/{id}/refunds`) and body shapes from `apps/api/schemas/invoice.py` and `payment.py`.

**Verify:** integration suite (+5), unit suite unchanged.

---

## D2. Tests: marketplace search and suspended tenant on a real DB

**Files:** new `apps/api/tests/integration/test_public_and_lifecycle.py`.

**Cases**
1. Two tenants, each with one product `marketplace_enabled = true` and one `false`. `GET /v1/marketplace/search?q=<common word>` (no tenant host) returns exactly the two opted-in products, each with its own tenant's name, never the opted-out ones.
2. Set tenant A `status = 'suspended'` (migrate role). Login on A → 404 "Unknown or inactive tenant" (core/tenant_context.py). Same for `canceled` and `pending`. `trialing` and `past_due` → login 200.
3. `GET /v1/storefront/products` on A's host lists only A's opted-in products.

Closes the REQ-BR-009 "non-empty marketplace results" check and REQ-BR-010 "suspended tenants cannot transact".

**Verify:** integration suite.

---

## D3. DB: marketplace search lists trialing and past_due shops

**Bug fixed:** `platform.search_public_marketplace_products` (migration 026) filters `t.status = 'active'`. Login allows `active`, `trialing` and `past_due` (`TRANSACTING_TENANT_STATUSES` in core/tenant_context.py), so a trialing or past-due shop can sell but its opted-in products are hidden from the marketplace. Found in D2; the user chose to list them (2026-11-27).

**Files:** new `database/migrations/035_marketplace_status.sql`, new `apps/api/tests/unit/test_migration_035.py`, `apps/api/tests/integration/test_public_and_lifecycle.py`.

**Steps**
1. 035: one `BEGIN; ... COMMIT;`. `CREATE OR REPLACE FUNCTION` with the same signature, body and `SECURITY DEFINER` / `search_path` as 026, but `t.status IN ('active', 'trialing', 'past_due')`. Repeat the `OWNER TO shopper_migrate`, `REVOKE ... FROM PUBLIC` and `GRANT EXECUTE ... TO shopper_app` lines. Safe to rerun.
2. Static test: the file has one BEGIN/COMMIT, the three statuses, `SECURITY DEFINER`, and the grant.
3. Integration: in `test_blocked_tenant_statuses_cannot_log_in_or_list`'s sibling for trialing and past_due, also assert shop A's listed product is in marketplace search.
4. Apply 035 twice on shopper_verify (asyncpg as postgres).

**Verify:** unit suite (+1 file), integration suite.

---

## E1. Mobile: API URL, shop code and request headers

**Bugs fixed:** `ApiClient.baseUrl` is the constant `https://api.shopper.com/v1`. The API finds the tenant from the host (`<tenant>.<root>/api/...`) or, in dev, `X-Shopper-Tenant`. The app sends neither, so every call is refused with 403.

**Files:** `shopper-mobile/lib/data/sources/remote/api_client.dart`, `lib/data/sources/local/preferences/app_preferences.dart`, new `lib/core/config/api_config.dart`, `test/` new `api_config_test.dart`, `shopper-mobile/README.md` (run command).

**Steps**
1. `api_config.dart`:
   ```dart
   class ApiConfig {
     static const urlTemplate = String.fromEnvironment('SHOPPER_API_URL', defaultValue: 'https://{tenant}.shopper.com/api');
     static String baseFor(String tenant) => urlTemplate.replaceAll('{tenant}', tenant).replaceAll(RegExp(r'/+$'), '');
   }
   ```
   Dev: `flutter run --dart-define=SHOPPER_API_URL=http://10.0.2.2:8000` (no `{tenant}`; the header carries it, needs `ALLOW_TENANT_OVERRIDE=true` on the API).
2. `AppPreferences`: `getTenantCode()/setTenantCode(String)` and `getBranchId()/setBranchId(String?)` (SharedPreferences keys `tenant_code`, `branch_id`).
3. `ApiClient`: replace the constant with `Future<String> _base()` = `ApiConfig.baseFor(tenant)` + `/v1`. Every `Uri.parse('$baseUrl/...')` becomes `Uri.parse('${await _base()}/...')`. Paths keep their `/tenant/...` part. `_getHeaders()` adds `X-Shopper-Tenant: <tenant>` and, when set, `X-Shopper-Branch: <branchId>`.
4. Test: `baseFor('acme')` with the default template gives `https://acme.shopper.com/api`; headers include the tenant.

**Verify:** `flutter test`, `flutter analyze`.

---

## E2. Mobile: login matches the API

**Bugs fixed:** the app posts `{email, password}` to `/v1/auth/login`; the API takes `{username, password}` at `/v1/tenant/auth/login` and returns only `access_token` and `token_type`. `/auth/refresh` and `/auth/me` do not exist.

**Files:** `api_client.dart`, `lib/data/repositories/auth_repository.dart`, `lib/domain/repositories/auth_repository.dart`, the login use case, bloc and screen (find with `grep -rn "login(" lib test`), `lib/domain/entities/auth_token.dart`, tests under `test/` that mock login, `en`/`bn` strings if the app has them.

**Steps**
1. `ApiClient.login({required String tenant, required String username, required String password})`: save the tenant with `setTenantCode` first, POST `/tenant/auth/login` with `{'username': username, 'password': password}`. Build `AuthToken(accessToken: data['access_token'], refreshToken: null, expiresAt: <JWT exp>)`; decode the JWT payload (base64url middle part) for `exp`, `uid`, `role`.
2. Make `AuthToken.refreshToken` nullable if it is not.
3. Delete `ApiClient.refreshToken` and `getCurrentUser`. `AuthRepository.getCurrentUser()` builds `User` from the stored token's claims (`id = uid`, `role`, `name = username` saved at login, `email = ''`). `refreshToken()` returns `Left(AuthFailure('Session expired'))` and the bloc logs out.
4. `_handleResponse`: on 401 when a token was sent → clear the token (preferences) and return an `AuthFailure`, so the bloc shows the login screen.
5. Login screen: fields Shop code, Username, Password (rename the email field, keep validation non-empty). Rename the chain `email` → `username` and add `tenant`.
6. Update tests that mocked `login(email: ...)`. Add a test that the request body is `{"username","password"}` and the path ends with `/v1/tenant/auth/login`, using a `MockClient` from `package:http/testing.dart`.

**Verify:** `flutter test`, `flutter analyze`. Manual check when the API runs locally: log in as the seeded staff.

---

## E3. Mobile: products from /pos/sync, remove dead calls

**Bugs fixed:** `getProducts` calls `/v1/products` (does not exist) and expects `{"products": [...]}` with fields `price`, `brand`, `variants`; the API's product list is a bare list with `sell_price`. `ApiClient.createOrder` posts to `/v1/orders` (does not exist) and is unused: orders are saved locally and sent with `offline-punch`.

**Files:** `api_client.dart`, `lib/data/repositories/product_repository_impl.dart`, tests for product sync.

**Steps**
1. Replace `getProducts` with `fetchPosCatalog()` → `GET /tenant/pos/sync`, returning `{branch_id, categories, products}`. Map each product: `id`, `sku`, `nameEn = name_en`, `nameBn = name_bn`, `barcode`, `price = sellPrice = toDouble(sell_price)`, `taxRate = toDouble(vat_rate_pct)`, `isTaxable = taxRate > 0`, `stockQuantity = toDouble(stock_quantity).round()` (or keep double if the entity allows), `category = category name from categories by category_id`, `isActive = true`, `createdAt = updatedAt = DateTime.now()`. Add `double toDouble(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0` (the API may send numbers or strings).
2. Save `branch_id` from the response with `setBranchId` so later calls send the same branch.
3. `ProductRepositoryImpl`: use `fetchPosCatalog()`; search and category filters run on the local cache (the API has no server search for POS).
4. Delete `ApiClient.createOrder` and `syncPosData` (now `fetchPosCatalog`). `git grep` both names in `lib` and `test` to fix callers.
5. Tests: mapping from a sample `/pos/sync` body with Decimal-as-string and number values.

**Acceptance:** stock shown is the till branch's stock (closes "per-branch stock in mobile").
**Verify:** `flutter test`, `flutter analyze`.

---

## E4. Contract check: openapi.json and a mobile path test

**Files:** new `apps/api/scripts/export_openapi.py`, new `docs/openapi.json`, new `apps/api/tests/unit/test_openapi_current.py`, new `shopper-mobile/test/api_paths_test.dart`.

**Steps**
1. `export_openapi.py`: set `TESTING=1`, import `main.app`, write `json.dumps(app.openapi(), indent=2, sort_keys=True)` to `docs/openapi.json`.
2. `test_openapi_current.py`: regenerate in memory and compare with the file; on mismatch fail with "run python scripts/export_openapi.py".
3. `api_paths_test.dart`: read `../docs/openapi.json`, collect `paths`; read `lib/data/sources/remote/api_client.dart` as text, extract every `'/tenant/...` path literal after `_base()` (regex `\$\{await _base\(\)\}(/[a-z0-9/_{}$-]+)`), replace `$var` parts with `{x}`, and assert each `/v1` + path exists in the spec (compare with `{...}` segments normalised).
4. Every later API change that touches routes must rerun the export (add this line to AGENTS.md "After a change").

**Verify:** API suite, `flutter test`.

---

## F1. Web: branches screen

API exists: `GET /v1/tenant/branches` (staff), `POST` and `PATCH /{id}` (admin).

**Files:** new `src/app/features/branches/branch.service.ts`, `branches-page.component.ts` (+ specs), `app.routes.ts`, `core/nav/nav-items.ts` (add the `/branches` item from B2), `en.json`, `bn.json`.

**Steps:** list (name, code, main, active), create form (name, code), edit name and active flag. Disable the active switch on the main branch. The API also refuses (409, show its `detail` in the row): deactivating the main branch, deactivating a branch that still holds stock, and a duplicate code on create. Route guarded by `roleGuard(['admin'])`. Strings under `branches.*`.

**Verify:** web tests (+2 specs) and build.

---

## F2. DB+API: branch on invoices and POS sales (migration 034)

**Files:** new `database/migrations/034_invoice_branch.sql`, `test_migration_034.py`, `routers/invoices.py`, `routers/pos.py`, `schemas/invoice.py` (`InvoiceOut.branch_id`), integration test additions in `test_commerce_flows.py`.

**Steps**
1. 034: `ALTER TABLE tenant_data.invoices ADD COLUMN IF NOT EXISTS branch_id UUID;` backfill each tenant's invoices to its main branch; composite FK `(tenant_id, branch_id) → branches (tenant_id, id)` NOT VALID + VALIDATE (same pattern as 032); index `(tenant_id, branch_id, created_at)`. Leave it nullable for rows of tenants with no branch.
2. `POST /invoices` takes `BranchDep`, resolves it and stores `branch_id`. `issue` and `cancel` take stock from and return it to `invoice.branch_id` (fallback main branch when NULL), not the request's branch. Today `cancel_invoice` has no `BranchDep`; find which branch `_restock_at_sale_cost` and the issue path use (`git grep -n "_restock_at_sale_cost\|def issue_invoice" apps/api/routers/invoices.py`) and pass `invoice.branch_id` to both. Offline-punch already resolves a branch; store it on the invoice it creates.
3. Tests: static 034 test; integration: an invoice created with header branch B issues stock from B even when issued with header A.

**Verify:** API unit and integration suites.

---

## G1. CI: run on dev2, add web unit tests and Flutter

**File:** `.github/workflows/ci.yml`.

**Steps:** add `dev2` to `push` and `pull_request` branches. In `web-build` add `- run: npx ng test --watch=false --browsers=ChromeHeadless` before the build (ubuntu-latest has Chrome). New job `mobile` with `subosito/flutter-action@v2` (channel stable), `working-directory: shopper-mobile`, `flutter pub get`, `flutter analyze`, `flutter test`. Keep `docker-build-push` on main/master only.

**Verify:** `docker compose -f docker-compose.yml config --quiet` still passes; the workflow file parses (`python -c "import yaml,sys;yaml.safe_load(open('.github/workflows/ci.yml'))"`). The real check is the first CI run on dev2.

---

## G2. Repo: remove one-off scripts, mark old docs historical

**Steps**
1. `git rm apps/api/fix_kwargs.py apps/api/fix_routers.py apps/api/fix_sql.py apps/api/refactor.py scratch/clean_emojis.py` (nothing imports or runs them: checked with `git grep` on 2026-11-13). Keep `seed_db.py` and `run_and_start.bat` (local dev entry points).
2. Done in P0: `docs/Shopper-Refactor-Plan.md` and `docs/COMPREHENSIVE_ARCHITECTURE_SECURITY_REVIEW.md` carry the "Historical (superseded)" line. Check it is still there.

**Verify:** API suite unchanged.

---

## G3. Docs close-out

Run once, after the last non-blocked session. On 2026-11-13 a status pass already added known-issue notes to DEPLOY.md, ARCHITECTURE_AND_SECURITY_REVIEW.md, the web and mobile READMEs, and a "Changes since 2026-04-20" list at the top of ARCHITECTURE_MAP.md. G3 removes the known-issue notes that the sessions fixed and merges that list into the map's sections.

On 2026-11-27 the user asked for an early docs pass covering A1 to A4, B1 to B7, C1, C2 and D1 to D3. README, DEPLOY (migrations, URLs, isolation suite), the security review, the web README, the ARCHITECTURE_MAP change list, tasks.md and the spec's "Tested" lines are current up to D3. G3 now only adds what the later sessions change, and it still has to merge the map's change list into its sections.

1. Rerun all suites; write the counts and date in README "Verification status".
2. DEPLOY.md: `STOREFRONT_PUBLIC_BASE_URL` must be host style (A2); gateway URLs it produces; mobile `SHOPPER_API_URL` (E1); migrations up to 034; precheck before 032 on real data.
3. ARCHITECTURE_MAP.md: refresh "Last Updated", list new files (storefront_url, checkout return route, tenant settings store, nav items, guards, branches page, migrations 032-034, openapi export).
4. spec.md: tick the acceptance criteria now covered by integration tests (REQ-BR-002/003/004/005/009/010).
5. tasks.md: replace "Still open" with what is left (blocked items only) and the new baselines.
6. AGENTS.md and `.claude/memory`: update "Current state" and the baselines.

---

## Blocked and deferred

| ID | Item | Why not now | What unblocks it, then what to do |
|---|---|---|---|
| X1 | bKash, Nagad, Rocket gateways (Rocket returns 501; bKash and Nagad fail closed) | No provider API contracts | Contracts with sandbox keys. Then: add a gateway class like `SSLCommerzGateway` with provider-verified callback (transaction, order, amount, currency, terminal status), tests with recorded sandbox responses, keep fail-closed when keys are missing. |
| X2 | Per-branch FIFO costing | Accounting policy decision (D5) | User decides per-branch or tenant-wide cost layers. Then: `cost_layers.branch_id` migration and COGS by branch. |
| X3 | API enforcement of `module_access` | D3 | User asks for it. Then: a dependency `ModuleDep("inventory")` that returns 403 when off, applied per router; mobile must handle 403 on `pos`. |
| X4 | Live deploy checks | Needs the real host | Wildcard DNS and TLS for `*.<root>`; one SSLCommerz sandbox payment end to end (initiate → gateway → return page → IPN marks it completed); printed QR opens the right tenant. |
| X5 | Storefront orders taking stock | There is no storefront ordering; the storefront lists products and pays existing invoices | A storefront ordering feature is specified. Not a defect. |
| X6 | QR link expiry per tenant | D5: stays an app setting | Closed. Reopen only if a tenant asks. |

## Plan review (2026-11-13)

Checked while writing this plan, so the sessions do not open new defects:
- A1 widens read access to settings. `TenantSettingsOut` has no gateway secrets (they are only in `TenantSettingsInternalOut`).
- A2 relies on openresty stripping `/api/` on the tenant host (`infra/openresty/nginx.conf`) and on the IPN route accepting a tenant-less host with `?tenant=` (main.py middleware). Path-style base URLs would break it; G3 documents that.
- A3 changes roles. The web hides the forms for roles that now get 403, so no page shows a button that always fails.
- B1/B2 guards allow the route while settings are loading or failed, so an API hiccup cannot lock staff out; the API keeps enforcing roles.
- B2 keeps `/admin/tenants` reachable by URL, so the platform admin flow is unchanged.
- C1 keeps each link's delete rule. `SET NULL (col)` is required for composite FKs (else `tenant_id` would be nulled) and needs PostgreSQL 15+. A failed precheck stops the migration (it is one transaction), so nothing is half applied.
- C1 drops the 025/026 composite FKs that used NO ACTION next to a CASCADE/SET NULL one-column FK; deleting a category with products or an invoice with payments could fail on those. C2 tests both deletes.
- A4 and D1 use their own random tenants and clean up, so they never touch other data in the scratch DB.
- E2 removes refresh: the API has no refresh endpoint, so the app logs out on expiry instead of looping.
- E3 keeps orders local-first through offline-punch, which already exists and is tested.
- F2 makes cancel return stock to the invoice's own branch, not the caller's.
- Web unit tests could not be rerun on 2026-11-13. The first web session runs them first and records the baseline in its row before editing.
