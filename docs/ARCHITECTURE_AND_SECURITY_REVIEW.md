# Shopper — Architecture, Security & QA Review (Historical; Superseded)

**Review note (2026-10-20):** This document's previous "hardened and verified" statements were unsupported and are withdrawn. Current requirements and evidence are in [ShopperRequirements.txt](ShopperRequirements.txt) and [the platform tasks](../.specify/specs/shopper-platform/tasks.md).

---

## 1. Current Evidence Summary

The worktree contains implementation across these areas, but repository code and tests do not establish production readiness. Current remediation adds safeguards for offline settlement, stock availability, public marketplace exposure, category tenancy, and callback verification.

| Area | Current status |
|------|:---|
| Tenant isolation | Partially implemented; PostgreSQL RLS and migration integration checks remain unverified here. |
| Tenant error handling | Unknown-host requests return an explicit 403 response; route-level tenant resolution still needs database-backed verification. |
| Payments | SSLCommerz IPNs use provider-verified order/transaction/amount/currency. bKash/Nagad initiation and callbacks fail closed pending approved API contracts; Rocket gateway is not implemented. |
| Inventory/POS | Offline sales validate aggregate stock under row locks; schema migration and live rollback behavior remain unverified without PostgreSQL. |
| Marketplace | Product-level opt-in and a constrained database function are implemented; live RLS behavior remains unverified. |
| Reporting | Inventory-turnover COGS uses FIFO stock-movement costs; other report calculations require domain-specific verification. |
| API tests | Latest run: 69 passed, 19 skipped. |

---

## 2. Security Hardening & Isolation

### 2.1 Multi-Tenant Safety
- Tenant context and RLS policies are present in the schema and application paths; complete table coverage and runtime enforcement have not been independently verified.
- The API establishes transaction-scoped tenant context; database-backed isolation tests remain a release gate.
- Dedicated database routing code exists, but production routing behavior is not certified by the current test evidence.

### 2.2 Tamper-Evident Auditing
- Migration `015_audit_chaining.sql` defines hash chaining. Deployment state, complete trigger coverage, and tamper resistance have not been verified against a live database.

### 2.3 Webhook Security
- SSLCommerz callback claims are not trusted alone: server-side validation must return matching order, transaction, amount, and currency before settlement.
- bKash and Nagad callbacks are rejected with an unavailable response until provider-authenticated verification is implemented from approved provider documentation.
- Payment-row locking and database-derived balances remain the idempotency/reconciliation controls; they do not substitute for provider verification.

---

## 3. Financial & Regulatory Compliance

### 3.1 Mushak 6.3 Invoicing
- **Bilingual Layouts**: Native Bengali and English support for legal tax invoices.
- **Line-Level VAT**: Precise VAT calculations per item with automated register population.

### 3.2 Inventory Valuation
- **WAC (Weighted Average Cost)**: Real-time cost updates on every inward stock transaction.
- **FIFO (First-In, First-Out)**: Automatic layer depletion for outward movements, ensuring accurate profit/loss reporting.

---

## 4. Verification & QA

- The API suite reported 69 passed and 19 skipped on 2026-10-20.
- PostgreSQL migration, RLS, marketplace, and settlement checks are skipped without configured integration database credentials.
- Flutter tests currently include one failing product-repository assertion; the app is not release-verified.

---
**Review Status:** **IN PROGRESS — NOT PRODUCTION CERTIFIED**
