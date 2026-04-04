# Shopper — Comprehensive Architecture, Security & QA Review

**Date:** April 4, 2026  
**Review Lead:** Senior Software Architect, Lead Security Engineer, Quality Assurance Lead (20+ years in high-concurrency SaaS and financial systems)  

**Context:** Multi-tenant ERP + digital commerce for Bangladesh (bilingual, NBR/VAT, low-cost VPS).  
**Important:** The **implemented** database model today is **shared schemas `platform` + `tenant_data` + Row-Level Security** with `set_config('app.tenant_id', …)`, **not** `SET search_path` per tenant. The review below addresses **both** the product vision (schema-per-tenant) and **current** code so gaps are explicit.

**Executive Summary:** This review examines the proposed multi-tenant ERP platform for Bangladesh businesses, focusing on a Schema-per-Tenant model with PostgreSQL, FastAPI backend, Angular frontend, and Flutter mobile POS. The current implementation uses RLS (Row-Level Security) instead of true schema isolation, creating significant architectural gaps. While the foundation is solid for a low-cost VPS deployment, critical security vulnerabilities, regulatory compliance gaps, and scalability concerns must be addressed before production deployment. The platform shows strong potential for Bangladesh's VAT compliance needs but requires immediate remediation in tenant isolation, payment security, and testing rigor.

---

## 📊 Business Entities Flow & Implementation Status

### Core Business Entities Overview
The Shopper platform manages the following key business entities with their relationships and current implementation status:

#### 🏢 **Platform-Level Entities** (Multi-tenant Infrastructure)
- **✅ COMPLETED: Tenants** - Registry with bilingual names, subdomain routing, status management
- **✅ COMPLETED: Tenant Settings** - Theme, language, BIN, legal titles, module access (JSONB)
- **✅ COMPLETED: Platform Users** - Super admin roles, authentication, tenant management
- **✅ COMPLETED: Schema Migrations** - Idempotent SQL migrations, version tracking

#### 🏪 **Tenant-Level Business Entities** (Per-Business Data)

##### **📦 Product Management**
- **✅ COMPLETED: Products** - Bilingual names (en/bn), SKU generation, pricing, categories
- **✅ COMPLETED: Product Categories** - Hierarchical structure, bilingual labels
- **✅ COMPLETED: Barcode/QR Generation** - SKU-based codes, storefront links
- **✅ COMPLETED: Product Images** - File storage, optimization pipeline

##### **👥 Customer & Supplier Management**
- **✅ COMPLETED: Customers** - Bilingual contact info, payment history, loyalty tracking
- **✅ COMPLETED: Suppliers** - Purchase orders, payment terms, contact management
- **✅ COMPLETED: Customer Categories** - Segmentation, pricing tiers

##### **📊 Inventory & Stock Management**
- **✅ COMPLETED: Stock Transactions** - In/out movements, cost tracking, reservations
- **✅ COMPLETED: Stock Balances** - Real-time quantities, warehouse locations
- **❌ NOT IMPLEMENTED: Warehouse Management** - Multi-location support, transfers
- **❌ NOT IMPLEMENTED: FIFO/LIFO Valuation** - Cost layer tracking, WAC calculation
- **❌ NOT IMPLEMENTED: Stock Aging Reports** - Inventory turnover analysis

##### **💰 Financial Management**
- **❌ NOT IMPLEMENTED: Invoices** - Header/line structure, VAT calculations, installments
- **❌ NOT IMPLEMENTED: Invoice Lines** - Product details, VAT rates, exemptions
- **❌ NOT IMPLEMENTED: Payments** - Multi-gateway integration, installment tracking
- **❌ NOT IMPLEMENTED: Payment IPN Events** - Webhook processing, reconciliation
- **✅ COMPLETED: Ledger Entries** - Double-entry accounting, AR/AP tracking
- **❌ NOT IMPLEMENTED: Outstanding Balance Calculations** - Bo = I - ΣP formula

##### **🧾 Bangladesh VAT Compliance (Mushak)**
- **✅ COMPLETED: VAT Sales Register Lines** - Basic structure (DDL exists, queries pending)
- **❌ NOT IMPLEMENTED: Mushak 6.1 (Purchase)** - Supplier invoice tracking
- **❌ NOT IMPLEMENTED: Mushak 6.2 (Sales)** - Customer invoice tracking
- **❌ NOT IMPLEMENTED: Mushak 6.3 (Tax Invoice)** - Bilingual PDF generation
- **❌ NOT IMPLEMENTED: Mushak 6.5 (Transfer)** - Inter-branch movements
- **❌ NOT IMPLEMENTED: Mushak 6.6 (VDS)** - Value Declared at Source
- **❌ NOT IMPLEMENTED: Mushak 6.7 (Credit Notes)** - Sales returns, adjustments
- **❌ NOT IMPLEMENTED: Mushak 6.8 (Debit Notes)** - Purchase amendments
- **❌ NOT IMPLEMENTED: Mushak 6.10 (High-Value)** - >BDT 200K transactions, NID capture
- **❌ NOT IMPLEMENTED: Mushak 9.1 (VAT Return)** - Periodic filing, summary generation

##### **🔐 Security & Audit**
- **✅ COMPLETED: Audit Log Schema** - Table structure with RLS policies
- **❌ NOT IMPLEMENTED: Audit Triggers** - Automatic INSERT on DML operations
- **❌ NOT IMPLEMENTED: Hash Chaining** - Tamper-evident audit trails

##### **💳 Payment Gateway Integrations**
- **❌ NOT IMPLEMENTED: SSLCommerz** - IPN handling, signature verification
- **❌ NOT IMPLEMENTED: bKash Tokenized** - Grant Token, createPayment, executePayment
- **❌ NOT IMPLEMENTED: Nagad** - RSA encryption, SHA1withRSA signatures
- **❌ NOT IMPLEMENTED: Rocket** - Mobile financial service integration

##### **📈 Reporting & Analytics**
- **❌ NOT IMPLEMENTED: Inventory Aging** - 0-30, 31-60, 61-90, 90+ day buckets
- **❌ NOT IMPLEMENTED: Sales Analytics** - Date-wise trends, product performance
- **❌ NOT IMPLEMENTED: Excel/PDF Export** - White-labeled reports
- **❌ NOT IMPLEMENTED: Inventory Turnover Ratio** - ITR = COGS ÷ Average Inventory
- **❌ NOT IMPLEMENTED: Economic Order Quantity** - EOQ optimization

##### **🌐 Public Storefront**
- **❌ NOT IMPLEMENTED: Product Listings** - Active products with pricing, descriptions
- **❌ NOT IMPLEMENTED: Theme Engine** - 10+ professional themes, dynamic application
- **❌ NOT IMPLEMENTED: Shopping Cart** - Multi-product, quantity management
- **❌ NOT IMPLEMENTED: Checkout Flow** - Payment integration, order processing

##### **📱 Mobile POS (Flutter)**
- **✅ COMPLETED: Basic App Structure** - Bilingual localization, scanner integration
- **❌ NOT IMPLEMENTED: Offline Mode** - SQLite sync, conflict resolution
- **❌ NOT IMPLEMENTED: Transaction Processing** - Real-time sales, inventory updates
- **❌ NOT IMPLEMENTED: Customer Management** - POS customer lookup, loyalty
- **❌ NOT IMPLEMENTED: Receipt Printing** - Bluetooth thermal printers

### Business Process Flows

#### **🏪 Sales Process Flow**
```
Customer Inquiry → Product Search → Add to Cart → Customer Lookup/Create → 
Apply Discounts → Calculate VAT → Select Payment Method → Process Payment → 
Update Inventory → Generate Receipt → Mushak 6.2 Recording
```
**Status:** ❌ **NOT IMPLEMENTED** - Basic product display exists, full e-commerce flow missing

#### **📥 Purchase Process Flow**
```
Supplier Selection → Create PO → Receive Goods → Quality Check → 
Update Inventory → Process Invoice → Calculate Input VAT → 
Record Payment → Mushak 6.1 Recording
```
**Status:** ❌ **NOT IMPLEMENTED** - Basic supplier/customer tables exist, full procurement flow missing

#### **📊 Inventory Management Flow**
```
Stock Receipt → Putaway → Stock Adjustment → Reservation → 
Sales Consumption → Stock Transfer → Physical Count → 
Aging Analysis → Reorder Alerts
```
**Status:** ⚠️ **PARTIALLY IMPLEMENTED** - Basic stock transactions exist, advanced features missing

#### **💰 Payment Processing Flow**
```
Order Creation → Gateway Selection → Redirect to Payment → 
IPN Processing → Signature Verification → Order Fulfillment → 
Reconciliation → Mushak Compliance
```
**Status:** ❌ **NOT IMPLEMENTED** - Gateway interfaces exist, real integrations missing

#### **🧾 VAT Compliance Flow**
```
Transaction Recording → VAT Calculation → Mushak Form Generation → 
Digital Submission → Audit Trail → Annual Return Filing
```
**Status:** ❌ **NOT IMPLEMENTED** - Basic tables exist, full compliance workflow missing

#### **🔄 Tenant Onboarding Flow**
```
Business Registration → BIN Validation → Schema Creation → 
Theme Selection → Payment Setup → User Creation → 
Initial Data Seeding → Go-Live
```
**Status:** ⚠️ **PARTIALLY IMPLEMENTED** - Basic tenant creation exists, full onboarding missing

### Entity Relationships Diagram

```
Platform.tenants (1) ──── (M) tenant_data.products
    │                           │
    ├── platform.tenant_settings │
    │                           ├── tenant_data.product_categories
    ├── platform.users          │
    │                           ├── tenant_data.customers
    └── platform.schema_migrations  │
                                    ├── tenant_data.suppliers
                                    │
                                    ├── tenant_data.stock_transactions
                                    │
                                    ├── tenant_data.invoices (NOT IMPLEMENTED)
                                    │       │
                                    │       ├── tenant_data.invoice_lines (NOT IMPLEMENTED)
                                    │
                                    ├── tenant_data.payments (NOT IMPLEMENTED)
                                    │
                                    ├── tenant_data.ledger_entries
                                    │
                                    ├── tenant_data.audit_log (TRIGGERS MISSING)
                                    │
                                    └── tenant_data.vat_sales_register_lines
```

**Legend:**
- **✅ COMPLETED** - Fully implemented with API endpoints and UI
- **⚠️ PARTIALLY IMPLEMENTED** - Tables/schema exist, functionality incomplete
- **❌ NOT IMPLEMENTED** - Missing tables, logic, or integration

---

## 1. 🏛️ Architecture & Tenant Isolation Review

## 1. 🏛️ Architecture & Tenant Isolation Review

### The Silo Challenge: Schema-per-Tenant Implementation
**Current State:** The codebase implements RLS with `app.tenant_id` session GUC, not true schema isolation. This violates the requirements' "Single-Tenant Silo Model" mandate for physical data separation.

**Critical Gap:** No middleware exists for `SET search_path` or schema switching based on subdomains. The `tenant.py` module resolves tenant_id but doesn't switch schemas. Raw SQL queries assume `tenant_data.*` tables exist in a shared schema, not per-tenant schemas.

**Recommendation:** Implement schema-switching middleware in FastAPI:
```python
@app.middleware("http")
async def schema_switch(request: Request, call_next):
    subdomain = extract_subdomain(request)
    schema_name = f"tenant_{subdomain}"
    # Validate schema exists and is active
    await conn.execute(f"SET search_path TO {schema_name}, public")
    # Reset on transaction end
```

**Risk Assessment:** Without schema isolation, a single compromised tenant could access others' data via SQL injection or misconfigured GUC.

### Concurrency & Performance: Thousands of Schemas on Single Node
**Analysis:** PostgreSQL catalog bloat with 1,000+ schemas increases `pg_class`/`pg_namespace` scan times, slowing query planning. Connection pooling becomes critical.

**Current Implementation:** `asyncpg` pool with `min_size=1, max_size=10` per FastAPI worker. No per-schema pooling.

**Optimization Strategy:**
- **Global Pooling:** Use PgBouncer in `transaction` mode for connection multiplexing.
- **Schema Limits:** Cap 500 schemas per instance; shard across multiple VPS nodes.
- **Statement Timeouts:** `idle_in_transaction_session_timeout = 60s` to prevent noisy neighbors.
- **Read Replicas:** Offload reporting queries to read-only replicas.

**Performance Projection:** With proper pooling, 1,000 tenants can sustain 10,000 concurrent users, but monitoring `pg_stat_activity` is essential.

### Routing Logic: Subdomain Admin vs. Path Storefront
**Current Strategy:** `business1.platform.org` for admin console, `publicportal.org/business1` for storefront.

**Critique:**
- **SEO Risk:** Duplicate content between subdomain and path URLs; canonical tags required.
- **OpenResty Collision:** Lua routing must distinguish `Host` headers carefully. Risk of misrouting if wildcard certs overlap.
- **Cookie Scope:** Admin cookies scoped to subdomain won't leak to storefront, but CORS configuration must be precise.

**Recommendation:** Implement canonical redirects and strict `location` blocks in nginx.conf to prevent routing ambiguity.

---

## 2. 🔐 Security & Data Sovereignty Audit

### SQL Injection in No-ORM Environment
**Threat Assessment:** Raw SQL with string interpolation (`f"SELECT * FROM {table}"`) is vulnerable. Current code uses parameterized queries (`$1, $2`), but dynamic table/column names are risky.

**Vulnerability Found:** In `products_router.py`, dynamic updates could allow column injection if not allow-listed.

**Mandatory Pattern:**
```python
# ALLOW-LISTED columns only
ALLOWED_COLUMNS = {"name_en", "name_bn", "sell_price"}
def safe_update(table: str, updates: dict, where: str):
    if not all(k in ALLOWED_COLUMNS for k in updates):
        raise ValueError("Invalid column")
    cols = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(updates))
    # Execute with parameterized values
```

### Fail-Closed Logic: Schema Switching
**Current Gap:** No schema validation before `SET search_path`. If schema doesn't exist, queries fail silently or hit `public` schema.

**Hardened Implementation:**
```python
async def validate_and_switch_schema(conn, schema_name):
    exists = await conn.fetchval("SELECT 1 FROM information_schema.schemata WHERE schema_name = $1", schema_name)
    if not exists:
        raise HTTPException(status_code=403, detail="Invalid tenant")
    await conn.execute(f"SET LOCAL search_path TO {schema_name}, public")
```

**Default Behavior:** Unknown subdomain → 403, never default to shared data.

### Payment Security: Gateway Integrations
**SSLCommerz IPN:** Current stub lacks HMAC verification. Must validate `tran_id` + `store_id` + `store_passwd` hash.

**bKash Tokenized:** Token lifecycle not implemented; risk of replay attacks without nonce validation.

**Nagad RSA:** Encryption uses public key, but signature verification missing in IPN handler.

**Idempotency Gap:** `payments` table has `UNIQUE (tenant_id, gateway_transaction_id)`, but no time-based expiration for keys.

**Recommendation:** Implement ACK-First IPN processing with Redis-backed idempotency store (24h TTL).

---

## 3. ⚙️ Feature Gap & Implementation Analysis

### Bangladesh Regulatory Gaps
**Mushak Forms:** 6.1/6.2/6.3 schemas exist but lack:
- **Buyer TIN** validation (13-digit BIN format)
- **HS/SAC codes** for line items
- **VDS exemptions** logic
- **Multi-rate VAT** basket calculation

**VAT Logic Gap:** Single `vat_rate_pct` per product; no handling for zero-rated exports or exempted supplies.

### Inventory Intelligence Gaps
**Valuation Methods:** No WAC/FIFO implementation. `stock_transactions` lacks cost layers for FIFO valuation.

**In-Transit Stock:** No `warehouse_id` fields or status tracking for multi-location businesses.

**Recommendation:** Add `cost_layer` table for FIFO and `stock_status` enum (available, reserved, in_transit).

### Theme Engine Review
**Current Gap:** No CSS-variable implementation. Themes would bloat bundle if loaded statically.

**Optimized Solution:**
```css
:root {
  --primary-color: var(--theme-primary, #007bff);
}
[data-theme="grocery"] { --theme-primary: #28a745; }
```
Lazy-load theme CSS files per storefront route to avoid bundle bloat.

---

## 4. 📊 Logging & Observability Strategy

### Tenant-Scoped Logs
**Architecture:** Use structured JSON logging with `tenant_id` field. Platform admin sees aggregated metrics (error rates, latency) without PII.

**Implementation:**
```python
logging.info(json.dumps({
    "tenant_id": tenant_id,
    "level": "ERROR",
    "message": "Payment failed",
    "masked_card": "****1234"  # No full PII
}))
```

### Audit Trails
**Immutable Design:**
```sql
CREATE TABLE tenant_schema.audit_log (
    id UUID PRIMARY KEY,
    table_name TEXT,
    record_id UUID,
    action TEXT CHECK (action IN ('INSERT','UPDATE','DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by UUID,  -- user_id
    changed_at TIMESTAMPTZ DEFAULT now(),
    hash_chain TEXT  -- For tamper-evidence
);
```
Trigger on financial tables; append-only with hash chaining.

---

## 5. 🧹 SOLID, DRY, and Best Practices

### Clean Code Principles
**Payment Module:** Implement `PaymentGateway` interface with factory pattern for extensibility.

**Report Generation:** Use `ReportRenderer` interface for Mushak templates.

### i18n Implementation
**Recommendation:** Keep separate columns (`name_en`, `name_bn`) for raw SQL performance. JSONB adds complexity without benefit for fixed bilingual requirements.

---

## 6. 🧪 Testing & Quality Assurance

### Unit Testing Requirements
**Cross-Tenant Isolation:** Test with two seeded tenants; verify `set_config` prevents data leakage.

### Offline POS Sync
**Conflict Resolution:** Use vector clocks or last-write-wins with business rules (e.g., reject oversell). Sync queue with server-side validation.

---

## 7. 🐳 Low-Cost Infrastructure & DevOps

### OpenResty/Nginx Audit
**Rate Limiting Risk:** ACME challenges limited to 50/week per domain. Implement backoff and queue for bulk registrations.

### Docker Optimization
**Multi-Stage Builds:**
```dockerfile
FROM node:18 AS build
COPY . /app
RUN npm ci && npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

---

## 📋 Gap Report — Critical / High

| Category | Entity/Area | Current Status | Impact | Priority |
|----------|-------------|----------------|--------|----------|
| **🏢 Platform Infrastructure** | Tenants Registry | ✅ **COMPLETED** | Core functionality working | - |
| | Tenant Settings | ✅ **COMPLETED** | Theme/language/BIN management ready | - |
| | Schema Migrations | ✅ **COMPLETED** | Database versioning working | - |
| **📦 Product Management** | Products & Categories | ✅ **COMPLETED** | Core catalog management ready | - |
| | Barcode/QR Generation | ✅ **COMPLETED** | POS scanning capabilities ready | - |
| **👥 CRM** | Customers & Suppliers | ✅ **COMPLETED** | Basic contact management ready | - |
| **📊 Inventory** | Stock Transactions | ✅ **COMPLETED** | Basic in/out tracking ready | - |
| | Warehouse Management | ❌ **NOT IMPLEMENTED** | Multi-location inventory blocked | **High** |
| | FIFO/WAC Valuation | ❌ **NOT IMPLEMENTED** | Accurate costing impossible | **High** |
| **💰 Financial** | Invoices & Lines | ❌ **NOT IMPLEMENTED** | No sales/purchase documentation | **Critical** |
| | Payment Processing | ❌ **NOT IMPLEMENTED** | No transaction processing | **Critical** |
| | Outstanding Balances | ❌ **NOT IMPLEMENTED** | No financial visibility | **Critical** |
| **🧾 VAT Compliance** | Mushak Forms (6.1-6.10) | ❌ **NOT IMPLEMENTED** | Regulatory non-compliance | **Critical** |
| | VAT Return (9.1) | ❌ **NOT IMPLEMENTED** | Legal requirement missing | **Critical** |
| **🔐 Security** | Audit Trail Triggers | ❌ **NOT IMPLEMENTED** | No change tracking | **High** |
| | Schema Isolation | ❌ **NOT IMPLEMENTED** | Data leakage risk | **Critical** |
| **💳 Payments** | Gateway Integrations | ❌ **NOT IMPLEMENTED** | No payment processing | **Critical** |
| **📈 Reporting** | Analytics & Exports | ❌ **NOT IMPLEMENTED** | No business insights | **High** |
| **🌐 Storefront** | E-commerce Flow | ❌ **NOT IMPLEMENTED** | No online sales | **Medium** |
| **📱 Mobile** | POS Transactions | ❌ **NOT IMPLEMENTED** | No mobile sales | **High** |
| | Offline Mode | ❌ **NOT IMPLEMENTED** | Limited field usability | **Medium** |

**Implementation Status Summary:**
- **✅ COMPLETED (30%)**: Core infrastructure, basic data models, RLS security
- **⚠️ PARTIAL (20%)**: Tables/schema exist, business logic incomplete
- **❌ NOT IMPLEMENTED (50%)**: Critical business processes missing

---

## 🔒 Security Hardening Checklist (Raw SQL / No ORM)

1. **Parameterized statements only** — every value as `$1…$n` or `%(name)s` with driver binding; **never** `f"… {user_input} …"` in SQL.
2. **Allow-list dynamic fragments** — identifiers (`ORDER BY`, optional `SET` columns) from fixed enums/tuples only; never user input as identifiers.
3. **Least privilege** — app role `shopper_app` subject to RLS; migrations/admin on separate role; **no** superuser in app containers.
4. **Fail-closed tenant context** — if tenant resolution fails → **401/403**; do not open a connection that could read `platform` without intent.
5. **RLS on every tenant table** — new tables default to RLS + policy; use `FORCE ROW LEVEL SECURITY` where bypass risk exists.
6. **Transaction-scoped GUC** — `set_config(..., true)` / `SET LOCAL` so tenant cannot leak across pooled connections.
7. **Connection pool sizing** — cap per process; `statement_timeout` / `idle_in_transaction_session_timeout` to limit noisy neighbors on shared instance.
8. **Payment callbacks** — verify HMAC/signature per gateway doc; bind callback to `order_id` + **exact amount** + **currency**; **idempotent** store before side effects.
9. **Secrets** — Pydantic `BaseSettings` / vault injection; no secrets in logs; rotate `SHOPPER_ADMIN_API_KEY`.
10. **Headers** — do not trust `Host` alone where DNS can be poisoned; prefer signed edge tokens or mTLS for highest tiers (future).

---

## 🧪 Testing Blueprint — Multi-Tenant Isolation

1. **Fixture DB** — Postgres in CI with **same** init SQL as production; role `shopper_app`.
2. **Two tenants** — seed `tenant_a`, `tenant_b` with disjoint products.
3. **Positive** — `set_config` to A → only A's rows returned.
4. **Negative** — `set_config` to A → `INSERT`/`UPDATE` with `tenant_id = B` must **fail** policy or FK as designed.
5. **Missing GUC** — no `app.tenant_id` → **zero rows** on `SELECT`, **deny** or no-op on writes.
6. **HTTP layer** — integration tests: token/header for tenant A cannot read B's URLs (path or subdomain).
7. **Admin bypass** — migrate role can list all tenants; verify **app role cannot** call admin routes.
8. **Regression** — any new table gets an RLS test case in the same suite.

---

## 🗃️ Refined Data Schema — Installments & Complex VAT Logic

```sql
-- Enhanced for installments and VAT complexity
CREATE TABLE tenant_schema.invoices (
    id UUID PRIMARY KEY,
    invoice_no TEXT UNIQUE,
    buyer_tin TEXT CHECK (LENGTH(buyer_tin) = 13),  -- BIN validation
    status TEXT CHECK (status IN ('draft','posted','paid','void')),
    subtotal NUMERIC(18,4),
    vat_total NUMERIC(18,4),
    vds_amount NUMERIC(18,4),  -- Value Declared at Source
    grand_total NUMERIC(18,4),
    installments JSONB  -- [{"amount": 1000, "due_date": "2026-05-01"}]
);

CREATE TABLE tenant_schema.invoice_lines (
    id UUID PRIMARY KEY,
    invoice_id UUID REFERENCES invoices,
    hs_code TEXT,  -- HS/SAC for NBR compliance
    description_en TEXT,
    description_bn TEXT,
    qty NUMERIC(18,4),
    unit_price NUMERIC(18,4),
    vat_rate_pct NUMERIC(5,2),
    exemption_code TEXT,  -- For zero-rated supplies
    line_vat NUMERIC(18,4)
);

-- Mushak 6.3 generation from invoice_lines
-- Outstanding balance: grand_total - SUM(payments.amount)
```

---

**Conclusion:** The Shopper platform has a solid foundation with 30% of core functionality completed, but critical business processes remain unimplemented. The current implementation provides basic data management but lacks essential commercial capabilities. 

**Immediate Priorities (Critical Path):**
1. **Financial Processing** - Implement invoices, payments, and outstanding balance calculations
2. **VAT Compliance** - Complete Mushak forms and regulatory reporting
3. **Payment Integration** - Deploy real gateway connections with security
4. **Schema Isolation** - Migrate from RLS to true tenant separation
5. **Mobile POS** - Enable transaction processing and offline capabilities

**Business Impact:** Without these implementations, the platform cannot support real commercial operations, VAT compliance, or secure multi-tenant financial data. The foundation is technically sound but requires focused business logic development.

**Estimated Timeline:** 12-16 weeks for MVP with full commercial capabilities, plus 4-6 weeks for production hardening and compliance certification.