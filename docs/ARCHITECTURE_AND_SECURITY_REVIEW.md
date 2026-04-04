# Shopper — Architecture, Security & QA Review

**Context:** Multi-tenant ERP + digital commerce for Bangladesh (bilingual, NBR/VAT, low-cost VPS).  
**Important:** The **implemented** database model today is **shared schemas `platform` + `tenant_data` + Row-Level Security** with `set_config('app.tenant_id', …)`, **not** `SET search_path` per tenant. The review below addresses **both** the product vision (schema-per-tenant) and **current** code so gaps are explicit.

---

## 1. Gap Report — Critical / High

| Area | Gap | Severity |
|------|-----|----------|
| **Tenant model** | Spec mentions schema-per-tenant; code uses **RLS + `tenant_id`**. Mixing both without an ADR invites wrong queries and operational confusion. | **Critical** |
| **Fail-closed** | Missing/invalid `app.tenant_id` → **no rows** (good). Unknown subdomain on API still resolves in some dev paths (`localhost` → `demo`). Production must **403** inactive/unknown tenants **before** DB work. | **High** |
| **Mushak / VAT** | Only stub `vat_sales_register_lines`; no **invoices**, **line VAT**, **VDS**, **exemptions**, **BIN** on tenant, **6.3 layout** rules. VAT on products is a single `vat_rate_pct` — no multi-rate basket logic. | **Critical** (regulatory) |
| **Commercial** | **Payments** table + gateways stub exist; **storefront** product list + **inventory aging** report live; **invoices**/installment engine and **outstanding balance** still thin. | **High** |
| **Inventory** | **`stock_transactions`** exists (basic ledger); **WAC/FIFO**, reservations, in-transit, multi-warehouse still open. | **High** |
| **Payments** | **IPN route** + SSLCommerz `store_id`/`status` + amount binding + DB idempotent **completed** + **Redis** replay keys. **Remote `val_id` validation** still TODO. Other gateways **501**. | **High** (financial) |
| **Admin key** | `X-Shopper-Admin-Key` is a shared secret; no rotation, no audit of admin actions, TLS must be mandatory. | **High** |
| **ORM / SQL** | Raw SQL is fine if **100% parameterized**; dynamic `UPDATE` in products builds column list from pydantic — safe only if keys are **allow-listed** (currently yes; must stay enforced). | **Medium** |
| **Observability** | No tenant-tagged structured logs, no separate “platform ops” vs “tenant PII” streams. | **High** |
| **POS offline** | No sync protocol, conflict resolution, or “last unit” arbitration. | **High** |
| **i18n in UI** | Product UI still has some literals (e.g. confirm dialog); policy should be **all** strings from `assets/i18n`. | **Medium** |
| **Redis** | **Compose** + **async client** on API; **IPN idempotency** keys with TTL. **Tenant cache** + **rate-limit middleware** + **job queue** still TODO. | **Medium** |
| **CI** | **pytest**, **ng build**, **compose config** run on PR; **Docker push** optional on `main` when registry secrets exist; Flutter analyze optional. | **Low** |

---

## 2. Security Hardening Checklist (Raw SQL / No ORM)

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

## 3. Testing Blueprint — Multi-Tenant Isolation

1. **Fixture DB** — Postgres in CI with **same** init SQL as production; role `shopper_app`.
2. **Two tenants** — seed `tenant_a`, `tenant_b` with disjoint products.
3. **Positive** — `set_config` to A → only A’s rows returned.
4. **Negative** — `set_config` to A → `INSERT`/`UPDATE` with `tenant_id = B` must **fail** policy or FK as designed.
5. **Missing GUC** — no `app.tenant_id` → **zero rows** on `SELECT`, **deny** or no-op on writes.
6. **HTTP layer** — integration tests: token/header for tenant A cannot read B’s URLs (path or subdomain).
7. **Admin bypass** — migrate role can list all tenants; verify **app role cannot** call admin routes.
8. **Regression** — any new table gets an RLS test case in the same suite.

---

## 4. Architecture Deep Dive (concise)

### 4.1 Silo / schema vs RLS (current vs proposed)

- **Current:** One physical DB, `tenant_data.*` with `tenant_id` + RLS via `app.tenant_id`. **No** `search_path` switch.
- **Proposed in brief:** `SET search_path TO tenant_xyz, public` per request.

**Trade-offs**

- **RLS (current):** Fewer schemas to migrate; easier shared indexes; risk if a query **forgets** GUC (mitigated by RLS → empty set, not wrong tenant).
- **Schema-per-tenant:** Stronger cognitive isolation; **metadata bloat** (thousands of schemas) on one instance: slower catalog ops, heavier backups, migration fan-out. Needs **automation** and **pool discipline** (small pools, timeouts, optional **PgBouncer** in `transaction` pooling mode with care — GUC/session issues).

**Recommendation:** Document one strategy. If you stay RLS-only, rename docs to avoid “schema silo” confusion. If you move to schemas, add **middleware** that sets `search_path` **only** after subdomain→schema map validate, and **reset** on connection return to pool (or use `SET LOCAL` in transaction).

### 4.2 Concurrency & noisy neighbor

- Thousands of tenants on **one** node: limit **connections** per worker, use **timeouts**, partition heavy reporting to read replicas or batch jobs.
- **asyncpg pool:** `max_size` per instance bounded; consider **global** queue in front of DB (PgBouncer).
- **.NET / psycopg3:** same principles; `NpgsqlDataSource` with pool limits.

### 4.3 Routing: subdomain (admin) vs path (storefront)

- **Pros:** Clear separation of “console” vs “shop”; CDN-friendly for static storefront.
- **Risks:** Cookie scope, CORS, duplicate content SEO if same product on aggregator + tenant URL — use **canonical** links; OpenResty: **one** `server_name` / wildcard tree; avoid overlapping `location` regex that catches `/api` on storefront host.

---

## 5. Regulatory & Inventory Gaps (Bangladesh)

- **Mushak:** Need **legal entity** fields (BIN, address, invoice series), **buyer TIN**, line-level **HS/SAC**, **taxable value**, **VAT**, **SD** if applicable, **VDS** marker, **challan** linkage for 6.1/6.2.
- **Exemptions:** Schema for **reason code** + **certificate ref** per line or invoice.
- **Inventory:** **Stock ledger** (qty in/out, cost, ref doc); **WAC** = rolling average on each receipt; **FIFO** = layer table; **in-transit** = status on `stock_movements` + warehouse_id from/to.

---

## 6. Theme engine (Angular, low bundle bloat)

- **Design tokens** as CSS variables on `:root` or `data-theme="grocery"`: `--color-primary`, `--font-heading`, etc.
- **Ten themes** = ten small CSS files or one file with attribute selectors `[data-theme="…"]` loaded **lazy** per storefront route (not bundled in admin app if split apps).
- **tenant_settings.theme_id** drives `data-theme` at runtime.

---

## 7. Logging & audit

- **App logs:** JSON lines with `tenant_id`, `trace_id`, `user_id`, **no** raw card/OTP.
- **Platform:** Aggregate error rates per tenant **without** storing line-item payloads in shared indices (or encrypt).
- **Audit:** Append-only **`tenant_data.audit_log`**; **triggers** on `products`, `stock_transactions`, `payments`, `ledger_entries` (`database/migrations/008_audit_triggers.sql`). Optional **hash chain** for tamper-evidence on high-value tenants still TODO. Set `app.changed_by` in the API when user identity exists.

---

## 8. SOLID — payments & reports

- **`PaymentGateway` protocol/interface:** `create_session`, `parse_ipn`, `verify_ipn`.
- **Factory:** `get_gateway("bkash", tenant_credentials)`.
- **Reports:** `ReportRenderer` interface; Mushak templates implement it; **inject** logo/BIN from `tenant_settings`.

---

## 9. i18n storage: columns vs JSONB

- **`name_en` / `name_bn`:** Simple queries, clear constraints, good for **fixed** bilingual ERP + reports.
- **JSONB `names`:** Better for **many** locales later; slightly more complex SQL and indexing (`jsonb_path_ops` GIN where needed).

**Recommendation:** Keep **columns** for bn/en now; add JSONB only if you add a third language.

---

## 10. Offline POS & conflicts

- **Local queue** of events with **client-generated UUID** + **vector clock** or **version** per stock row.
- **Sync:** Server applies in order; on **oversell**, return **conflict** payload; POS must **void** or **reprice** line.
- **“Last unit”:** **Optimistic locking** (`version` on `stock_balance`) — second commit loses and must refresh.

---

## 11. OpenResty / Let’s Encrypt at scale

- **Risk:** Many new subdomains → many cert requests → **Let’s Encrypt rate limits**.
- **Mitigate:** Staging CA in dev; **wildcard cert** `*.platform.com` (DNS-01) if provider supports Lua automation; backoff + **queue** for HTTP-01; monitor failures.

---

## 12. Docker image size

- **Angular:** multi-stage Node build → **nginx:alpine** (already); add `npm ci --omit=dev`, strip source from final stage.
- **API:** `python:3.12-slim`, `--no-cache-dir`, non-root user, `.dockerignore` for tests/docs.

---

## 13. Refined data schema sketch — installments & VAT (PostgreSQL)

```sql
-- platform.tenant_settings (one row per tenant; or 1:1 with tenants)
CREATE TABLE platform.tenant_settings (
  tenant_id UUID PRIMARY KEY REFERENCES platform.tenants(id) ON DELETE CASCADE,
  theme_id TEXT NOT NULL DEFAULT 'default',
  default_language TEXT NOT NULL DEFAULT 'en' CHECK (default_language IN ('en','bn')),
  legal_title_en TEXT,
  legal_title_bn TEXT,
  bin TEXT,                 -- business identification for NBR
  logo_url TEXT,
  default_vat_rate_pct NUMERIC(5,2) DEFAULT 0,
  module_access JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Commercial core (tenant_data, RLS like other tables)
CREATE TABLE tenant_data.invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES platform.tenants(id) ON DELETE CASCADE,
  invoice_no TEXT NOT NULL,
  invoice_date DATE NOT NULL,
  buyer_tin TEXT,
  status TEXT NOT NULL CHECK (status IN ('draft','posted','void')),
  subtotal NUMERIC(18,4) NOT NULL DEFAULT 0,
  vat_total NUMERIC(18,4) NOT NULL DEFAULT 0,
  grand_total NUMERIC(18,4) NOT NULL DEFAULT 0,
  vds_applicable BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (tenant_id, invoice_no)
);

CREATE TABLE tenant_data.invoice_lines (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES platform.tenants(id) ON DELETE CASCADE,
  invoice_id UUID NOT NULL REFERENCES tenant_data.invoices(id) ON DELETE CASCADE,
  line_no INT NOT NULL,
  description_en TEXT,
  description_bn TEXT,
  hs_code TEXT,
  qty NUMERIC(18,4) NOT NULL,
  unit_price NUMERIC(18,4) NOT NULL,
  discount NUMERIC(18,4) NOT NULL DEFAULT 0,
  vat_rate_pct NUMERIC(5,2) NOT NULL,
  vat_exemption_code TEXT,
  line_taxable NUMERIC(18,4) NOT NULL,
  line_vat NUMERIC(18,4) NOT NULL,
  UNIQUE (invoice_id, line_no)
);

CREATE TABLE tenant_data.payments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES platform.tenants(id) ON DELETE CASCADE,
  invoice_id UUID NOT NULL REFERENCES tenant_data.invoices(id) ON DELETE CASCADE,
  paid_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  amount NUMERIC(18,4) NOT NULL,
  method TEXT NOT NULL,
  gateway_ref TEXT,
  idempotency_key TEXT,
  UNIQUE (tenant_id, idempotency_key)
);

-- Outstanding per invoice (materialized view or computed in query)
-- Bo = invoices.grand_total - COALESCE(SUM(payments.amount),0)

CREATE TABLE tenant_data.payment_ipn_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES platform.tenants(id) ON DELETE CASCADE,
  gateway TEXT NOT NULL,
  raw_payload_hash TEXT NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome TEXT NOT NULL,
  UNIQUE (tenant_id, gateway, raw_payload_hash)
);
```

Enable **RLS** + policies mirroring `products` on all new `tenant_data` tables.

---

## 14. References in repo

- Implemented RLS: `database/init/01_schema_rls.sql`
- Tenant settings: `database/migrations/002_tenant_settings.sql` (applied via `init/02_apply_migrations.sh` or `database/run_migrations.py`); API `GET /v1/tenant/settings`
- Payments + IPN: `apps/api/payments_router.py` — webhook `POST /v1/tenant/payments/ipn/{gateway}?tenant=<subdomain>`
- Redis: `apps/api/redis_client.py` — optional `app.state.redis`, IPN dedupe keys
- Storefront: `apps/api/storefront_router.py` — `GET /v1/storefront/products`
- Reports: `apps/api/reports_router.py` — `GET /v1/tenant/reports/inventory-aging`
- Audit triggers: `database/migrations/008_audit_triggers.sql`
- VAT stub (migrations path): `database/migrations/009_vat_sales_register_lines.sql` (also in init for fresh DBs)
- App settings: `apps/api/config.py` (Pydantic `BaseSettings`)
- Angular admin console: `apps/shopper-web` route `/admin/tenants`, interceptor `shopper-admin.interceptor.ts`
- Agent convention: `.cursor/rules/post-change-workflow.mdc` (update docs/tests/services after substantive changes)
- Tasks / backlog: `tasks.txt`
- Deploy: `docs/DEPLOY.md`
