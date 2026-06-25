from __future__ import annotations

import logging
from uuid import UUID
import asyncpg
from fastapi import HTTPException
from core.db import get_tenant_pool, get_main_pool

logger = logging.getLogger(__name__)

async def migrate_to_dedicated(
    request, 
    tenant_id: UUID, 
    source_db_name: str | None, 
    target_db_name: str
):
    """
    Moves all data for a specific tenant from one database to another.
    """
    source_pool = await get_tenant_pool(request, source_db_name)
    target_pool = await get_tenant_pool(request, target_db_name)

    # Tables to migrate (tenant-scoped)
    tables = [
        "customers",
        "product_categories",
        "products",
        "invoices",
        "invoice_lines",
        "payments",
        "stock_transactions",
        "vat_sales_register_lines"
    ]

    async with source_pool.acquire() as source_conn:
        async with target_pool.acquire() as target_conn:
            async with source_conn.transaction():
                async with target_conn.transaction():
                    for table in tables:
                        logger.info(f"Migrating table {table} for tenant {tenant_id}")
                        
                        # Fetch data from source
                        rows = await source_conn.fetch(
                            f"SELECT * FROM tenant_data.{table} WHERE tenant_id = $1",
                            tenant_id
                        )
                        
                        if not rows:
                            continue
                            
                        # Insert into target
                        # This is a naive implementation; in production, use COPY or batch inserts
                        columns = rows[0].keys()
                        col_names = ", ".join(columns)
                        placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
                        
                        insert_query = f"INSERT INTO tenant_data.{table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                        
                        for row in rows:
                            await target_conn.execute(insert_query, *row.values())

    logger.info(f"Successfully migrated tenant {tenant_id} to {target_db_name}")
    return True
