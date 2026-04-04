# Shopper Multi-Tenant ERP Platform

A comprehensive SaaS ERP platform for Bangladesh with bilingual support (English/Bangla), multi-tenancy via Row-Level Security (RLS), and integrated payment gateways.

## Architecture

- **Backend**: FastAPI (Python) with PostgreSQL, AsyncPG, Pydantic
- **Frontend**: Angular 17 (Web) + Flutter (Mobile POS)
- **Reverse Proxy**: OpenResty with Lua scripting and auto-SSL
- **Database**: PostgreSQL with RLS for tenant isolation
- **Payments**: SSLCommerz, bKash, Nagad, Rocket gateways
- **Deployment**: Docker Compose with CI/CD

## Features

- ✅ Multi-tenant ERP (products, customers, stock, ledger)
- ✅ Bilingual UI (en-IN locale, BDT currency)
- ✅ Payment processing with IPN handling
- ✅ Reporting and analytics
- ✅ Admin console for tenant management
- ✅ Public storefront per tenant
- ✅ RLS security with audit trails
- ✅ Structured JSON logging

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repo>
   cd Shopper
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Run with Docker Compose**:
   ```bash
   docker compose up --build
   ```

3. **Access**:
   - API: http://localhost:8000
   - Web: http://localhost:80 (via OpenResty)
   - Admin: http://localhost:8000/v1/admin/tenants (with X-Shopper-Admin-Key)

## Development

- **API**: `cd apps/api && python -m pytest`
- **Web**: `cd apps/shopper-web && npm install && ng serve`
- **Mobile**: `cd shopper-mobile && flutter run`

## Environment Variables

See `.env.example` for required settings (DB, payments, domains).

## Security

- Row-Level Security enforced at DB level
- Admin API with key-based auth
- HTTPS with Let's Encrypt auto-SSL
- Rate limiting and domain whitelisting

## License

[Your License Here]