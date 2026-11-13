# Shopper Platform Plan

## Objective
Align the repository’s implementation work to a requirement-driven SDD flow while preserving the existing architecture and documentation conventions.

## Architecture context
This project spans:
- FastAPI backend in [apps/api](../../../apps/api)
- Angular app in [apps/shopper-web](../../../apps/shopper-web)
- Flutter app in [shopper-mobile](../../../shopper-mobile)
- PostgreSQL schema and migrations in [database](../../../database)
- Business requirements in [docs/ShopperRequirements.txt](../../../docs/ShopperRequirements.txt)

## Phase plan
### Phase 1: Requirements alignment
- Confirm the authoritative requirement set and resolve conflicting documentation.
- Keep the business requirement file as source of truth.
- Record assumptions and unresolved gaps.

### Phase 2: Implementation readiness
- Trace major feature areas to existing code.
- Identify missing security, validation, and contract-alignment work.
- Record gaps explicitly instead of claiming completion.

### Phase 3: Execution and verification
- Implement changes against REQ- identifiers.
- Add or update tests for the covered requirement.
- Refresh docs when behavior, environment, or deployment assumptions change.

## Current review remediation plan (2026-10-20)
### Phase A: Requirements and decisions
- Keep `docs/ShopperRequirements.txt` authoritative and record the approved offline payment, mobile tender, marketplace visibility, stock, COGS, and fail-closed provider decisions.
- Keep provider API integration explicitly blocked until approved bKash/Nagad verification contracts are supplied; do not accept unverified callbacks as a workaround.

### Phase B: Schema and contract corrections
- Add the missing non-negative product stock column and product-level marketplace opt-in to fresh initialization and a forward migration.
- Enforce tenant-qualified product-category references.
- Add a distinct issued/unpaid invoice status while preserving draft semantics.
- Align mobile POS tender identifiers and API validation.

### Phase C: Transaction integrity and safe exposure
- Record actual offline collections only; represent omitted amounts as unpaid, credit as zero collection, and reject overpayment.
- Validate aggregate POS demand under product row locks before releasing stock.
- Route public marketplace reads through a fixed, narrowly scoped database function returning only opted-in active listings.
- Compute COGS from inventory movement cost, not retail line prices.
- Return explicit client errors for unresolved tenant context.
- Fail closed on callback verification until provider details are available; verify SSLCommerz transaction fields against the matched local payment.

### Phase D: Verification and release gates
- Add focused unit/API/database integration tests for each corrected behavior.
- Run available backend tests and Flutter checks; run migration/RLS tests on PostgreSQL when configured.
- Keep database migration application and live provider verification marked pending if external infrastructure/contracts are unavailable.

## Current implementation plan (2026-11-13)
All remaining work, its order, dependencies, tests and acceptance criteria are in [the master plan](../../../docs/superpowers/plans/2026-11-13-master-plan.md). Phases: A API fixes, B web, C tenant-qualified foreign keys, D DB-backed tests, E mobile/API contract, F branch features, G CI, cleanup and docs. External gates (gateway contracts, live deploy checks) are listed there as blocked items.

## Dependencies and constraints
- Not all code paths are validated yet; implementation tasks must remain evidence-based.
- The repo has multiple planning documents; they must be reconciled before major assumptions are treated as final.
- Tenant isolation, auditability, and payment security remain priority constraints.

## Exit criteria
- Each major requirement has an explicit implementation owner and verification path.
- No requirement is treated as “done” without evidence or a documented debt note.
- Spec, plan, tasks, and implementation remain in sync.
- Every review finding is either fixed with focused evidence or explicitly blocked by a documented external prerequisite.
