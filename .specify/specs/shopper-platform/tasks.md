# Shopper Platform Tasks

## Priority A: requirement alignment
- [x] Confirm requirement source of truth in [docs/ShopperRequirements.txt](../../../docs/ShopperRequirements.txt)
- [x] Record repository evidence and unresolved issues in the spec
- [x] Keep implementation status separate from intended behavior

## Priority B: tenant and security
- [ ] REQ-BR-001 — Tenant model and routing
- [ ] REQ-BR-002 — Tenant isolation and access control
- [ ] REQ-NFR-001 — Security by default
- [ ] REQ-NFR-002 — Auditability

## Priority C: commerce operations
- [ ] REQ-BR-003 — Product catalog management
- [ ] REQ-BR-004 — Sales and invoice lifecycle
- [ ] REQ-BR-005 — Inventory control and stock movement
- [ ] REQ-BR-006 — Offline POS sync and offline punch
- [ ] REQ-BR-007 — Payments and gateways

### Current commerce implementation evidence
- [x] Validate non-negative product prices and stock, and lock products during stock adjustments.
- [x] Keep stock receipts, adjustments, and transfers tenant-scoped and aligned with on-hand quantities.
- [x] Persist invoice discounts and invoice lines with tenant IDs; keep draft invoices inventory-neutral.
- [x] Include allocated POS discounts in VAT register rows, reports, and exports.
- [x] Record sale returns against original invoice lines and reject quantities beyond the unreturned balance.
- [x] Make offline POS sync replay-safe and roll back failures per order.
- [ ] Run database-backed integration tests for product, invoice, return, and POS flows.
- [x] Add location-level stock balances so branch transfers preserve destination inventory. Done 2026-10-23 with migration 030 (branches, stock_levels) and services/stock.py.

### Payment and settlement implementation evidence
- [x] Require positive, precision-bounded payment amounts and associate gateway payments with invoices.
- [x] Lock invoices and reserve against pending plus completed payments before starting another installment.
- [x] Derive invoice paid/balance/status values from completed gateway and POS settlement records.
- [x] Record only collected amounts for finalized offline POS sales; omitted `amount_paid` means unpaid, while a missing tender retains the API's cash default.
- [x] Match successful IPNs to amounts, avoid downgrading completed payments, and allow failed callbacks to be followed by a later success.
- [x] Apply migrations 025 and 026 against PostgreSQL. Done 2026-10-24: migrations 01 to 031 applied on local Postgres 18.2 (scratch DB). Payment initiation and callbacks were not run against live gateways.
- [x] Fail closed for bKash/Nagad initiation and callbacks until approved provider-authenticated verification contracts are available.
- [ ] Implement Rocket gateway initiation and verification; it is currently declared in the API enum but returns 501.

## User-prioritized execution queue
- [x] REQ-BR-007 — Implement callback verification boundaries and reconcile completed payments against invoice balances; live PostgreSQL verification remains pending.
- [ ] REQ-BR-008/009/010 — Verify reports, storefront, marketplace, and admin business flows.
  - [x] Fix marketplace search failing on undefined database-pool access, observed in smoke tests.
  - [x] Return the expected unavailable-database response when tenant pool state is absent.
  - [ ] Verify non-empty global marketplace results through an explicitly public, RLS-safe data path; current smoke tests run without PostgreSQL.
- [ ] REQ-BR-002 / REQ-NFR-001/002 — Complete tenant-isolation, security, and audit validation.
  - [x] Bind staff JWT tenant claims to the resolved request tenant and limit the no-token development bypass to testing mode.
  - [x] Explicitly prevent the shopper_app database role from being superuser or bypassing RLS.
  - [x] Add tenant-qualified foreign keys and PostgreSQL assertions for settlement visibility and cross-tenant invoice references.
  - [x] Run RLS integration checks against a configured PostgreSQL app-role connection. Done 2026-11-06 on the scratch DB as a login role that is a member of shopper_app: all 6 tests in test_rls_isolation.py pass (see the handoff notes for the command).

## Review remediation queue (2026-10-20)
- [x] Record approved behavior: omitted POS `amount_paid` means unpaid; specific MFS choices; product-level marketplace opt-in; provider callbacks fail closed without provider contracts.
- [x] REQ-BR-003 — Add product stock to schema/migrations and enforce tenant-qualified category references.
- [x] REQ-BR-004/006/007 — Record offline partial payments accurately; omitted amount means zero; add issued invoice status; zero settlement for credit/unpaid sales; reject overpayment.
- [x] REQ-BR-005/006 — Validate aggregate stock availability under row locks and enforce non-negative DB quantity.
- [x] REQ-BR-006/007 — Align mobile and API tender values for bKash/Nagad/Rocket, card, cash, and credit.
- [x] REQ-BR-007 — Fail closed for unsupported bKash/Nagad verification and compare SSLCommerz provider-verified order, transaction, amount, currency, and status with the local payment. Full bKash/Nagad support is blocked on approved provider API details.
- [x] REQ-BR-008 — Calculate ITR COGS from stock movement/FIFO cost evidence.
- [x] REQ-BR-009 — Add default-private product marketplace opt-in and constrained RLS-safe public search function.
- [x] REQ-BR-001 — Return explicit 403 response from tenant middleware when tenant resolution fails.
- [x] Add focused unit/API coverage for the corrected behavior.
- [x] Run PostgreSQL migration/RLS verification. Done 2026-10-24 on a local scratch DB, as the shopper_app role: all migrations applied, 027/030/031 reran cleanly, and a refund and RLS smoke test passed.
- [x] Fix local product barcode mapping and declare `mocktail` as a direct test dependency; full Flutter tests pass and `flutter analyze` is clean.
- [x] Update release/task evidence after implementation and validation; retain external integration and database deployment gates as pending.

## Review remediation and leftovers (2026-10-23 to 2026-10-24)
Plans, with per-task notes: [review remediation](../../../docs/superpowers/plans/2026-10-23-review-remediation.md), [per-branch stock](../../../docs/superpowers/plans/2026-10-23-per-branch-stock.md), [leftovers](../../../docs/superpowers/plans/2026-10-23-leftovers.md).

- [x] Phase 1 of the review: tenant onboarding, startup refuses weak secrets (JWT_SECRET_KEY is required), storefront respects marketplace opt-in, payment integrity, report fixes, DB hardening (027), mobile sends 2-decimal money.
- [x] Phase 2: per-branch stock (030), web marketplace switch and search on products, /payments review page.
- [x] Leftovers (031): debit note fix, one purchase-return route, legacy transfer table dropped when empty, transfer by product_id, POS sync per branch, staff.branch_id limits cashier and accountant to their branch, fewer audit rows.
- [x] Leftover features: web login (/login, auth guard, Bearer interceptor), invoice issue and cancel on the web, public /checkout/:id pay-link page, payment refunds (payment_refunds table, POST and GET /v1/tenant/payments/{id}/refunds, "Record refund" on /payments).
- [x] Migration 019: the po_lines policy used a tenant_id column that po_lines does not have, so every fresh DB failed at 019. Fixed.
- [x] Printed invoice QR links last PRINTED_CHECKOUT_LINK_DAYS days (default 30, range 1 to 365). Links shown on screen still last 24 hours.
- [x] GET /v1/tenant/payments/{id}/refunds returns 404 for an unknown payment.
- [x] PATCH /v1/tenant/products/{id} with stock_quantity returns 409 when another branch holds stock. Use /v1/tenant/inventory/adjust for per-branch changes.
- [x] GET /v1/tenant/settings fixed (it returned 500). PATCH /v1/tenant/settings added, manager only, body TenantSettingsUpdate. Both checked on the scratch DB.
- [x] Review fixes (2026-11-06):
  - A refund on a completed payment frees that amount, so the invoice can be paid again (reserve_invoice_payment now matches refresh_invoice_balance).
  - The web interceptor sends a 401 to /login only when a token was sent. Checkout customers have no token and stay on the page.
  - docker-compose defaults ALLOW_TENANT_OVERRIDE to false.
  - Purchase returns need a received PO. Each product must be on the PO, and the total returned cannot pass the PO line qty. Cost comes from the PO line, not today's buy_price. The PO total drops by cost without VAT; the debit note keeps the VAT.
  - Checkout error messages are translated (checkout.noPaymentPage, checkout.payFailed).

### Still open
- [x] Printed QR links and gateway return URLs now put the tenant subdomain in front of STOREFRONT_PUBLIC_BASE_URL (core/storefront_url.py), or fill a `{subdomain}` placeholder in it (2026-11-06). Wildcard DNS and TLS must cover the host. Still check on the real deploy.
- [x] Product QR payloads now use the subdomain rule (`https://{sub}.{base}/p/{sku}`) through core/storefront_url.py, like invoice QR links (2026-11-06). No backfill: products created before this keep the old path-prefix payload until they are edited or recreated.
- [ ] Rocket gateway returns 501. bKash and Nagad fail closed until provider contracts arrive.
- [ ] Foreign key checks bypass RLS. A tenant who knows another tenant's row UUID could reference it. Low risk, not fixed.
- [x] Web /settings page for tenant settings (manager only), 2026-11-06: route, nav link, PATCH in the service, page, spec and en/bn strings. Shared form parts (field, notice, segmented, switch) and the --shopper-muted/-tint/-focus-ring/-danger tokens moved to src/styles.scss so the page style fits the budget (2.73 kB; warns over 2 kB, fails over 4 kB). Checked in a browser at 1440, 390 and 360 px (no sideways scroll, save sends only changed fields).
- [x] Web layout and theme fixes, 2026-11-06 (commit a086c86 plus later uncommitted work):
  - Header nav has its own row that scrolls sideways at every width. Phones now get a nav. The current page is marked and kept in view.
  - tailwind.config.js maps the shopper-* colors to the --shopper-* tokens with color-mix. Classes like bg-shopper-primary/10 and hover:bg-shopper-* now emit CSS. Before this they did nothing on every page.
  - Header theme dots use each theme's own primary. Theme names are translated (settings.themeNames).
  - Tokens added for the six themes that had none. Cyberpunk primary darkened to #d000d0 so white text passes 4.5:1.
  - Footer translated (footer.rights), dead "Security / Privacy / Infrastructure" items removed. Logo is a real link. EN/BN buttons have aria-pressed.
  - .animate-in (used on 12 pages) is defined in styles.scss. No Tailwind plugin provides it. Off under reduced motion.
- [ ] Web: look over all pages once. The Tailwind color fix turned on tints and hover colors that never showed before.
- [ ] Web: hide nav links for modules switched off in settings. Show the Admin link only to admins (check how roles reach the web first).
- [ ] Web: warn before leaving /settings with unsaved changes (canDeactivate).
- [ ] Web: no theme switch on screens under 1024 px except the /settings page.
- [ ] Web: browser test for /settings at 360 px in Bangla (no sideways scroll).
- [ ] Repo: add .gitattributes. Every commit warns about LF/CRLF.
- [ ] The QR link expiry is an app setting. It could move into platform.tenant_settings if each tenant needs its own value.
- [x] DB-backed RLS integration tests run against the scratch DB (2026-11-06): 11 passed, 1 skipped. The test cleanup deleted tenants directly, which failed: the cascade hits audited tables, and their audit trigger writes a row for a tenant that is already gone (audit_log_tenant_id_fkey). Cleanup now deletes the audited rows and audit_log rows first. The app itself never deletes tenants.
- [ ] test_pos_e2e.py still skips. It runs only when TESTING is unset, and it needs a seeded `demo` tenant with an admin/password staff login. Product, invoice and return flows have no DB-backed test yet (see "Run database-backed integration tests" above).
- [ ] Out of scope from the per-branch stock plan: per-branch FIFO costing, branch on invoices and POS sales, a branches screen on the web, per-branch stock in mobile, storefront orders taking stock.

### Handoff notes
- API tests: `python -m pytest -q` in apps/api. Last run on 2026-11-06: 318 passed, 19 skipped. Web (2026-11-06): 60 passed.
- Integration tests, from apps/api, on a scratch DB only: set `INTEGRATION_TEST=1`, `MIGRATE_DATABASE_URL` (a superuser or migrate role, used to seed and clean up), `DATABASE_URL` (a login role with shopper_app's rights and no BYPASSRLS) and a `JWT_SECRET_KEY` of 32+ chars, then `python -m pytest tests/integration -q`. Locally the shopper_app password is unknown, so a test role was made: `CREATE ROLE shopper_verify_app LOGIN PASSWORD '...' NOSUPERUSER NOBYPASSRLS IN ROLE shopper_app` (drop it with `DROP ROLE shopper_verify_app`).
- Web tests: `npx ng test --watch=false --browsers=ChromeHeadless` and `npx ng build` in apps/shopper-web.
- Migrations are numbered SQL files in database/migrations, applied in order by database/init/02_apply_migrations.sh or database/run_migrations.py. Each must be safe to rerun. The next number is 032.
- Check migrations on a throwaway scratch database, never on a shared or production one.
- The asyncpg pool has no JSONB codec. JSONB columns come back as text, so parse them, and write them as json.dumps(...) with a ::jsonb cast.
- Lock order for stock: lock product rows (services.stock.lock_products) before lock_levels. A tenant-row lock taken before an audit insert must use FOR NO KEY UPDATE, or it deadlocks with the audit trigger's advisory lock.

## Priority D: reporting and platform
- [ ] REQ-BR-008 — Reporting and compliance
- [ ] REQ-BR-009 — Public storefront and marketplace
- [ ] REQ-BR-010 — Admin and platform controls

## Definition of done
- Requirement is traceable to a business requirement ID.
- Acceptance criteria are explicit.
- Verification evidence exists or the gap is documented as a technical debt item.
- Documentation and tests reflect the latest behavior.
