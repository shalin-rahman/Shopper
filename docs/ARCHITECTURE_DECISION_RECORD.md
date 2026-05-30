# Architecture Decision Record: Hybrid Tenant Isolation Strategy

## Context

Shopper is a multi-tenant SaaS platform. We require rigorous data isolation while maintaining operational flexibility for both small (SMB) and large (Enterprise) tenants.

## Decision: Hybrid Isolation Model

We have transitioned from a pure RLS model to a **Hybrid Isolation Model**.

1.  **Shared RLS (Standard Tenants)**: Standard tenants reside in the common `tenant_data` schema, isolated via Row-Level Security (RLS) and transaction-scoped GUC (`app.tenant_id`).
2.  **Dedicated Database (Premium Tenants)**: High-tier tenants can be routed to their own physically separate database instances via dynamic connection routing in `tenant.py`.

## Rationale

-   **Scalability**: Shared RLS keeps overhead low for thousands of small tenants, while Dedicated DBs allow us to scale "noisy neighbors" or high-compliance enterprise clients independently.
-   **Security**: Both models leverage RLS as a baseline safety net. Dedicated DBs provide an additional physical boundary.
-   **Flexibility**: The `resolve_tenant_id` logic seamlessly switches between the shared pool and dedicated pools based on the tenant's `dedicated_database_name` configuration.

## Implementation Details

-   **Routing**: Handled in `tenant.py` and `db.py`.
-   **Security**: Every transaction starts with `SET LOCAL app.tenant_id`, ensuring RLS is active even on dedicated instances (for consistent code behavior).
-   **Safety**: If a tenant's routing cannot be resolved, the system fails-closed with a 403 Forbidden.

## Consequences

-   **Positive**: Accommodates Diverse workloads; minimal cross-tenant leakage risk; enterprise-ready.
-   **Operational Change**: Migrators must now handle both shared and dedicated connection strings.

## Status: REPLACED (Old RLS-only ADR) -> [ACTIVE]