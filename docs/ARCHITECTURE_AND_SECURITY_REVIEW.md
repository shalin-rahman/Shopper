# Shopper — Architecture, Security & QA Review (Post-Hardening)

**Context:** Multi-tenant ERP + digital commerce for Bangladesh (bilingual, Mushak 6.3/6.1 compliant, hardened multi-tenant isolation).

---

## 1. Executive Summary (Hardening Phase Complete)

All critical architectural and security gaps identified in the April 2026 review have been addressed. The platform now features robust multi-tenant isolation, compliant fiscal reporting, and tamper-evident auditing.

| Area | Status | Resolution |
|------|:---:|:---|
| **Tenant Isolation** | **STABLE** | Implemented dynamic routing supporting both Shared RLS and Dedicated Database schemas. |
| **Fail-Closed Safety**| **STABLE** | Subdomain resolution returns 404/401 proactively; RLS enforced at transaction level. |
| **Mushak / VAT** | **STABLE** | Full Mushak 6.3/6.1 bilingual support (Thermal & PDF) for Invoices and Sales Registers. |
| **Payments** | **STABLE** | Integrated SSLCommerz, bKash, and Nagad with remote validation and IPN idempotency. |
| **Inventory** | **STABLE** | WAC and FIFO cost layering implemented via materialized `wac_cost` and `cost_layers`. |
| **Security Audit** | **STABLE** | SHA-256 hash chaining of audit logs for complete tamper-evidence. |
| **POS Offline** | **STABLE** | High-performance sync protocol with FTS5 search (10k+ SKUs) and conflict resolution. |

---

## 2. Security Hardening & Isolation

### 2.1 Multi-Tenant Safety
- **RLS Enforced**: Every table in `tenant_data` uses `FORCE ROW LEVEL SECURITY`.
- **GUC Scope**: Tenant context is strictly bound to `app.tenant_id` within a `SET LOCAL` transaction block.
- **Dedicated DB**: High-performance tenants can be routed to dedicated PostgreSQL instances via `dedicated_database_name` routing.

### 2.2 Tamper-Evident Auditing
- **Audit Chain**: `015_audit_chaining.sql` implements a cryptographic chain where each audit record contains a hash of its content + the previous record's hash (SHA-256).
- **Immutable Log**: Triggers ensure that any change to critical tables (Products, Stock, Payments) is logged with a verifiable hash.

### 2.3 Webhook Security (HMAC/IPN)
- **Signature Verification**: Gateway callbacks (bKash/Nagad/SSLCommerz) are validated via remote API checks and local HMAC signature verification.
- **Idempotency**: Redis-backed suppression prevents replay attacks on financial triggers.

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

- **Isolation Suite**: `test_isolation.py` proves zero leakage between tenant data sets.
- **Full Flow Test**: `test_pos_e2e.py` verifies the entire lifecycle from scan/punch to fiscal sync.
- **Unit Test Coverage**: Cross-platform tests for billing math, theme services, and core logic.

---
**Review Status:** **[HARDENED & VERIFIED]**
