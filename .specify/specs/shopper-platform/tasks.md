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
- [ ] Add location-level stock balances so branch transfers preserve destination inventory.

### Payment and settlement implementation evidence
- [x] Require positive, precision-bounded payment amounts and associate gateway payments with invoices.
- [x] Lock invoices and reserve against pending plus completed payments before starting another installment.
- [x] Derive invoice paid/balance/status values from completed gateway and POS settlement records.
- [x] Record only collected amounts for finalized offline POS sales; omitted `amount_paid` means unpaid, while a missing tender retains the API's cash default.
- [x] Match successful IPNs to amounts, avoid downgrading completed payments, and allow failed callbacks to be followed by a later success.
- [ ] Apply migrations 025 and 026 and verify payment initiation, callback replay, installment, and POS settlement behavior against PostgreSQL.
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
  - [ ] Run RLS integration checks against a configured PostgreSQL app-role connection; skipped without integration configuration.

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
- [ ] Run PostgreSQL migration/RLS verification; no configured integration database is available in this environment.
- [x] Update release/task evidence after implementation and validation; retain external integration and database deployment gates as pending.

## Priority D: reporting and platform
- [ ] REQ-BR-008 — Reporting and compliance
- [ ] REQ-BR-009 — Public storefront and marketplace
- [ ] REQ-BR-010 — Admin and platform controls

## Definition of done
- Requirement is traceable to a business requirement ID.
- Acceptance criteria are explicit.
- Verification evidence exists or the gap is documented as a technical debt item.
- Documentation and tests reflect the latest behavior.
