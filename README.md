# Shopper Multi-Tenant ERP Platform (Hardened)

A production-grade SaaS ERP platform for Bangladesh with bilingual support (English/Bengali), deep multi-tenancy isolation via RLS and Dedicated Databases, and hardened financial infrastructure.

## 🚀 Architecture

- **Backend**: FastAPI (Python 3.11+) with PostgreSQL (AsyncPG), Redis (IPN Idempotency), and Pydantic.
- **Frontend**: Angular 17+ (Web Dashboard) + Flutter (Mobile POS).
- **Database**: Advanced PostgreSQL schema with SHA-256 Audit Chaining and Row-Level Security (RLS).
- **Isolation**: Dynamic resolving of shared RLS or Dedicated Database instances per tenant.
- **Payments**: Integrated SSLCommerz, bKash, and Nagad core with IPN validation.
- **Reporting**: Mushak 6.3/6.1 compliant bilingual invoicing and stock valuation (WAC/FIFO).

## ✨ Key Features

- **Hardened Multi-Tenancy**: Zero-leakage verified isolation with automatic subdomain-to-tenant mapping.
- **Offline-First POS**: High-performance mobile sync protocol with FTS5 search (10k+ SKUs) and Bluetooth thermal printing.
- **Bilingual Invoicing**: Full English/Bengali support for Tax Invoices (PDF) and POS Receipts (ESC/POS).
- **Inventory Intelligence**: Weighted Average Cost (WAC) and FIFO layering with stock aging and valuation reports.
- **Tamper-Evident Audit**: SHA-256 hash-chaining of all DML operations for financial integrity.
- **Multi-Theme Engine**: 10+ premium palettes (Cyberpunk, Emerald, etc.) across Mobile and Web platforms.
- **SaaS Lifecycle & Dunning**: Automated 14-day grace period enforcement and database lockdown routines.
- **Global Data Aggregation**: Cross-tenant marketplace API for `publicportal.org` discovery features.
- **Hardware Integrations**: POS ESC/POS receipt printing + PDF 1D Thermal Barcode sticker generation (Code128).

## 🛠️ Quick Start

1. **Setup Environment**:
   ```bash
   cp .env.example .env
   # Configure DATABASE_URL, REDIS_URL, and Gateway credentials
   ```

2. **Deploy with Docker**:
   ```bash
   docker compose up --build
   ```

3. **Verify Installation**:
   - Backend: `GET http://localhost:8000/health`
   - Master Roadmap: View [tasks.txt](./tasks.txt) for 100% completion status.

## 🧪 Testing & QA

| Component | Command | Target |
|-----------|---------|---------|
| **API** | `cd apps/api && pytest` | Unit & Integration (Isolation, Billing, E2E POS) |
| **Mobile** | `cd shopper-mobile && flutter test` | Core Units (Theme, Logic) |
| **Web** | `cd apps/shopper-web && ng test --watch=false` | Core Services (Theme, I18n) |

## 🛡️ Security

- **RLS Safety**: transaction-scoped `app.tenant_id` and `app.changed_by` GUCs.
- **Audit Chaining**: Verifiable hash-chain on `tenant_data.audit_log`.
- **RBAC**: Multi-role enforcement (Staff, Accountant, Manager) on all management routes.
- **HMAC**: Mandatory signature verification for external gateway webhooks.

## 📊 Documentation

Detailed technical documentation and implementation plans are available in the artifact reports.
- **Final Report**: [final_project_report.md](./final_project_report.md)
- **Roadmap**: [tasks.txt](./tasks.txt)

---
**Status:** **[PRODUCTION READY]**
