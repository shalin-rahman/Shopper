# Architecture Decision Record: Tenant Isolation Strategy

## Context

Shopper is a multi-tenant SaaS platform with shared PostgreSQL database. We need to enforce tenant data isolation at the database level to prevent accidental cross-tenant data leaks.

Two primary approaches were considered:

1. **RLS + `tenant_data` schema + `set_config('app.tenant_id')`** (current implementation)
2. **`SET search_path` schema-per-tenant** (alternative)

## Decision

We will stick with **RLS + `tenant_data` schema + `set_config('app.tenant_id')`** for production.

### Rationale

- **Simplicity**: Single schema (`tenant_data`) with RLS policies is easier to manage than per-tenant schemas.
- **Performance**: No need for `SET search_path` per request, which can complicate connection pooling and caching.
- **Migration**: Easier to add new tenants without schema creation overhead.
- **Security**: RLS provides a clear, enforceable boundary with `app_tenant_id()` function.
- **Scalability**: Works well with connection pooling (e.g., asyncpg pools) without search_path conflicts.
- **Existing Investment**: Already implemented and tested with integration harness.

### Alternatives Considered

#### Schema-per-Tenant (`SET search_path`)

- **Pros**: Complete isolation at schema level; no RLS overhead; easier auditing per tenant.
- **Cons**: Complex connection management (pool exhaustion if many tenants); harder migrations; requires schema creation per tenant; potential noisy neighbor issues with statement timeouts.

**Rejected because**: Increases operational complexity and doesn't align with our shared-database, RLS-first security model.

## Consequences

- **Positive**: Maintains current architecture; easy to extend with new tenant-scoped tables.
- **Negative**: None significant; RLS is performant for our use case.
- **Mitigations**: Monitor RLS policy performance; consider partitioning if tenant data grows massively.

## Migration Path (if needed)

If switching to schema-per-tenant in the future:

1. Create migration script to generate per-tenant schemas (`tenant_{subdomain}`).
2. Update `tenant.py` to use `SET search_path` instead of `set_config`.
3. Remove RLS policies; rely on schema isolation.
4. Update connection pooling to handle search_path resets.
5. Test thoroughly with integration harness.

## References

- PostgreSQL RLS docs: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Current schema: `database/init/01_schema_rls.sql`
- Integration tests: `apps/api/tests/test_integration_rls.py`