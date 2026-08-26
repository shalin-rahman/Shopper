# Shopper Platform — Comprehensive Implementation & Refactoring Plan

## Goal Description

The objective is to restructure the project documentation for better clarity and to execute the remaining steps of the comprehensive refactoring plan for the Shopper multi-tenant ERP platform. 

This plan has been updated to comprehensively incorporate **all architectural, security, and business requirements** defined across the project's documentation suite (including `ShopperRequirements.txt`, `ARCHITECTURE_AND_SECURITY_REVIEW.md`, and the existing Refactoring Plan). It ensures the system perfectly aligns with the required Mushak compliance, Hybrid Tenancy Isolation, tamper-evident auditing, and localized payment/fintech integrations.

## Open Questions

> [!IMPORTANT]
> **Documentation Location:** I plan to move `ShopperRequirments.txt`, `ShopperRequirments.docx`, and `ARCHITECTURE_MAP.md` into the `docs/` folder to declutter the root directory. Is it okay to also move `TODO.md` into `docs/`, or do you prefer it stays in the root directory?
> 
> **Mobile Refactor Scope:** There are significant compilation errors in the Flutter app. Should I prioritize fixing the Flutter build errors before proceeding with the mobile architectural refactoring (Phase 7)?

## Proposed Changes

### 1. Documentation Reorganization
We will consolidate all loose documentation files into the `docs/` folder to maintain a clean repository root.

#### [MODIFY] [README.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/README.md)
#### [NEW] [docs/ShopperRequirements.txt](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/docs/ShopperRequirements.txt)
#### [NEW] [docs/ShopperRequirements.docx](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/docs/ShopperRequirements.docx)
#### [NEW] [docs/ARCHITECTURE_MAP.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/docs/ARCHITECTURE_MAP.md)
#### [NEW] [docs/TODO.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/docs/TODO.md)
#### [NEW] [docs/mobile/COMPONENTS_README.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/docs/mobile/COMPONENTS_README.md)
#### [NEW] [docs/mobile/THEME_SYSTEM.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/docs/mobile/THEME_SYSTEM.md)
#### [NEW] [docs/mobile/VALIDATION_README.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/docs/mobile/VALIDATION_README.md)
#### [DELETE] [ShopperRequirments.txt](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/ShopperRequirments.txt)
#### [DELETE] [ShopperRequirments.docx](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/ShopperRequirments.docx)
#### [DELETE] [ARCHITECTURE_MAP.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/ARCHITECTURE_MAP.md)
#### [DELETE] [TODO.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/TODO.md)
#### [DELETE] [shopper-mobile/COMPONENTS_README.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/shopper-mobile/COMPONENTS_README.md)
#### [DELETE] [shopper-mobile/THEME_SYSTEM.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/shopper-mobile/THEME_SYSTEM.md)
#### [DELETE] [shopper-mobile/VALIDATION_README.md](file:///c:/Users/HabiburRahmanShalin/workstation/shaleen/ApplicationDevelopment/Shopper/shopper-mobile/VALIDATION_README.md)

---

### 2. Implementation Execution Plan

Below is the status and execution strategy, mapping the technical refactoring phases directly to the business requirements established in the documentation.

#### Phase 0: Pre-requisites & Security Hardening
*Addressing: Hybrid Isolation, Tamper-Evident Auditing, Secret Management*
- [x] Extract duplicated JWT `SECRET_KEY` into `config.py`. *(Completed)*
- [x] Fix relative imports in `tenant.py`. *(Completed)*
- [x] Delete duplicate dead mobile shell. *(Completed)*
- [x] Redact payment credentials (bKash, Nagad API keys) from `TenantSettingsOut` to prevent leakage. *(Completed)*
- [x] Verify SHA-256 Hash Chaining on the `audit_log` table is active for all financial tables. *(Completed - patched pgcrypto in migration 015)*
- [x] Fix wrong import depth & type issues for `OrdersBloc` in mobile. *(Completed)*

#### Phase 1: API Package Structure
*Addressing: Clean Architecture for ERP modules*
- [x] Restructure API into `core/`, `schemas/`, `routers/`, `services/`, and `utils/`. *(Completed)*
- [x] Split monolithic `schemas.py` into domain-specific files for Sales, Purchases, and Inventory. *(Completed)*

#### Phase 2: Tenant Context & RLS Isolation
*Addressing: Hybrid Tenancy Model (Shared RLS + Dedicated DBs)*
- [x] Replace the 8-line tenant resolution boilerplate repeated across 9 routers with the `TenantCtxDep` dependency injection. *(Completed)*
- [x] Ensure `SET LOCAL app.tenant_id` is robustly applied inside `TenantCtxDep` to guarantee RLS boundaries for shared pool tenants. *(Completed)*

#### Phase 3: Service Layer Extraction & Compliance Logic
*Addressing: Mushak 6.3/6.1/6.2/6.5/6.7/6.8/6.10, Installment Tracking, WAC/FIFO Valuation*
- [ ] **Pending:** Extract business logic from `routers/` (e.g., `products.py`, `invoices.py`) into the `services/` directory.
- [ ] **Pending:** Integrate Mushak generation logic within the Service Layer (e.g., automatically triggering Mushak 6.5 PDFs during stock transfers).
- [ ] **Pending:** Implement exact mathematical formulas for Outstanding Balance ($B_o = I_{total} - \sum P_i$) and Inventory Turnover within the `reports` and `invoices` services.
- [ ] **Pending:** Ensure Bi-lingual metadata (JSONB) fields are exposed correctly for Product and Customer schemas.

#### Phase 4: POS Validation, Offline-Sync & Fintech Webhooks
*Addressing: Offline-first Mobile Sync, bKash/Nagad Webhooks (IPN Idempotency)*
- [ ] **Pending:** Introduce `asyncio.Lock` around `DEDICATED_POOLS` in `core/db.py` to prevent race conditions during tenant DB provisioning.
- [ ] **Pending:** Create strict Pydantic schemas (`OfflinePunchOrder`) for `pos.py` to replace unvalidated `list[dict]` inputs coming from the offline-first Flutter mobile POS.
- [ ] **Pending:** Implement the "ACK-First" Webhook Idempotency pattern (Redis-backed queue, UUID validation) for SSLCommerz, bKash, and Nagad IPN listeners.
- [ ] **Pending:** Refactor mobile `ApiClient.baseUrl` from a hardcoded string to a configurable environment variable.

#### Phase 5: OpenAPI Contract & Frontend Alignment
*Addressing: Web Dashboard, Theming System*
- [ ] **Pending:** Generate and commit OpenAPI spec to `docs/openapi.json`.
- [ ] **Pending:** Align Angular `ProductService` models with the exact API response shape, including localized fields (`product_name_en`, `product_name_bn`).
- [ ] **Pending:** Implement auth token interceptor in the Angular web app.
- [ ] **Pending:** Align Flutter `ApiClient` endpoints and data models with the API.

#### Phase 6: Web Frontend Polish & Tests
*Addressing: Dunning Workflows, SaaS Billing, Theme Selection*
- [ ] **Pending:** Resolve conflict between `ThemeService` and `tenant-bootstrap.ts` regarding `data-theme` application (to support the 10+ professional niche themes requirement).
- [ ] **Pending:** Add Angular route guards for protected routes and SaaS subscription states (e.g., Trialing, Past Due, Suspended).
- [ ] **Pending:** Add unit tests for Angular components and API services.

#### Phase 7: Mobile App Native Features & Bi-lingual Support
*Addressing: High-Speed Scanning, Bi-lingual (Bangla/English) App UI*
- [ ] **Pending:** Add missing repository implementations in Flutter (`ProductRepository`, `CartRepository`, etc.).
- [ ] **Pending:** Register `SyncOrdersUseCase` in the GetIt dependency injection container.
- [ ] **Pending:** Implement robust language switching in `SettingsScreen` leveraging Flutter's l10n to support on-the-fly toggling between English and Bengali for POS retail staff.

## Verification Plan

### Automated Tests
- `pytest apps/api/tests/test_isolation.py` to ensure the API restructuring does not break Hybrid RLS tenant isolation.
- `pytest apps/api/tests/test_pos_e2e.py` to verify the full transaction lifecycle from POS punch to fiscal sync.
- `flutter analyze shopper-mobile` and `flutter test shopper-mobile` to verify Dart compilation and logic.

### Manual Verification
- Test Bi-lingual UI toggling in both the Angular and Flutter applications.
- Inspect the generated OpenAPI specification to ensure all routes and schemas are correctly documented.
- Perform a simulated webhook IPN hit to ensure Redis idempotency safely prevents duplicate payment logging.
