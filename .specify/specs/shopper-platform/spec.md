# Shopper Platform Specification

## Summary
The Shopper platform is a multi-tenant ERP and POS system for Bangladeshi businesses. It supports product, sales, purchase, inventory, customer and supplier management, financial reconciliation, billing, reporting, and public storefront capabilities across tenant boundaries.

## Scope
### In scope
- Multi-tenant tenant routing and access boundaries
- Product catalog and stock management
- Sales, invoice, and payment workflows
- Inventory movement and valuation
- VAT and reporting requirements
- Public storefront and marketplace flows
- Admin lifecycle and platform control

### Out of scope
- Unverified production-scale deployment assumptions
- Full public release claims without test evidence
- Process changes that contradict approved business constraints

## Actors
- Platform service provider / super admin
- Tenant admin / business owner
- Staff / cashier
- Accountant / financial user
- Customer / supplier

## Requirements
### REQ-BR-001: Tenant model and routing
- The platform shall support multiple business profiles, each associated with a tenant identity and a tenant-specific subdomain.
- Tenant resolution shall be based on request host or tenant header metadata.
- Unknown or inactive tenants must be rejected with explicit error responses.

Acceptance criteria:
- Valid tenant subdomains resolve to a tenant context.
- Invalid tenant context fails closed.
- Platform-level endpoints remain accessible when explicitly allowed.

### REQ-BR-002: Tenant isolation and access control
- Tenant data shall be isolated so one tenant cannot access another tenant’s records.
- Transaction-scoped tenant context must be established before data access.

Acceptance criteria:
- Tenant A data is not returned in queries for Tenant B.
- Missing or invalid tenant context fails closed.

### REQ-BR-003: Product catalog management
- The system shall allow a tenant to create, read, update, deactivate, and search products.
- Product metadata shall support bilingual names and stock state.

Acceptance criteria:
- A product is created with valid tenant-scoped identity, stock quantity, and SKU.
- Search results are scoped to the correct tenant.
- The initialized/migrated product schema contains stock quantity, enforces non-negative stock, and tenant-qualifies category references.

### REQ-BR-004: Sales and invoice lifecycle
- Invoice creation, line items, VAT, and balance tracking shall be supported.
- Partial or installment settlement shall remain auditable.

Acceptance criteria:
- Invoice totals reconcile to underlying line items and taxes.
- A partially paid invoice retains correct balance due.
- Unpaid finalized offline sales retain the full balance due and are not represented as drafts.
- Offline POS settlement equals the collected amount; omitted `amount_paid` means unpaid and overpayment is rejected.

### REQ-BR-005: Inventory control and stock movement
- Stock-in and stock-out events shall update inventory and preserve audit evidence.

Acceptance criteria:
- Stock-out reduces product quantity and reconciles with invoice or sale data.
- Failed steps cause transaction rollback rather than partial state.
- POS sync rejects aggregate demand greater than locked, available stock.

### REQ-BR-006: Offline POS sync and offline punch
- The system shall support offline mobile sales capture and later synchronization.
- Offline orders shall be validated before insertion.

Acceptance criteria:
- The mobile app calls only routes the API serves, with the tenant and branch the API expects (checked against docs/openapi.json, master plan E4).
- Valid orders sync successfully.
- Invalid payloads are rejected with clear error semantics.
- Mobile tender values are API-compatible, with explicit bKash/Nagad/Rocket choices and zero-settlement credit sales.

### REQ-BR-007: Payments and gateways
- The platform shall support Bangladesh payment methods and verify callbacks safely.
- Duplicate callbacks must not create multiple journal or inventory effects.

Acceptance criteria:
- Callback replay is rejected or safely deduplicated.
- Payment state remains consistent with invoice balances.
- Provider callbacks cannot complete payments without provider-authenticated evidence matching transaction, order, amount, currency, and terminal status.
- Gateway callbacks fail closed while provider verification integration is unavailable.

### REQ-BR-008: Reporting and compliance
- The system shall generate tenant-scoped reports and VAT-related outputs.

Acceptance criteria:
- Reports contain only tenant-owned records.
- VAT output matches transaction evidence.
- Inventory-turnover COGS uses recorded inventory cost, not selling price.

### REQ-BR-009: Public storefront and marketplace
- Public or storefront flows shall remain scoped to the appropriate tenant.

Acceptance criteria:
- Market listings do not mix different tenant product sets.
- Product listings require explicit product-level public opt-in and use a constrained RLS-safe public query path.

### REQ-BR-010: Admin and platform controls
- Super admin functions shall provide tenant lifecycle management and platform controls.

Acceptance criteria:
- Money-moving tenant endpoints (account transfers, supplier payments) require accountant, manager or admin; staff creation requires admin.
- Only authorized global users can manage platform state.
- Suspended or inactive tenants cannot process new transactions.

## Risks and assumptions
- The repo contains both completed and incomplete areas; the spec must not claim production readiness without verification.
- Some documents use different architecture descriptions; the issue is resolved by treating the code and requirement docs as evidence, not as an automatic proof of completion.
- Test coverage is not yet fully implemented across all domains.
- Approved bKash/Nagad verification API contracts are not currently available. Those callbacks must fail closed; verified provider integration remains a release gate.

## Approved decisions (2026-10-20)
- Offline `amount_paid` is the actual collection; omitted means unpaid; overpayment is rejected; zero collection creates no settlement. The selected POS tender is retained on the invoice. Credit requires zero collection. Unpaid finalized sales use an issued invoice status distinct from draft.
- Mobile MFS is represented by separate bKash, Nagad, and Rocket values. Gateway initiation support is a separate capability.
- Marketplace visibility defaults off per product and requires an explicit opt-in.
- POS stock checks aggregate repeated product lines while holding row locks.
- Product stock is present and non-negative in both fresh schema initialization and the forward migration; product categories are tenant-qualified.
- COGS for inventory turnover is based on stock-movement cost evidence.

## Traceability
- Source requirement file: [docs/ShopperRequirements.txt](../../../docs/ShopperRequirements.txt)
- Implementation evidence: [apps/api](../../../apps/api)
- Status tracking: [tasks.md](tasks.md); open work: [master plan](../../../docs/superpowers/plans/2026-11-13-master-plan.md)
- Verification status: automated evidence in apps/api/tests (unit and integration) and the web and mobile suites; see tasks.md
