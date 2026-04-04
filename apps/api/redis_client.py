"""Optional Redis (async). Used for payment IPN replay suppression and future tenant-scoped cache."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def build_ipn_idempotency_key(tenant_subdomain: str, gateway: str, order_ref: str, gw_txn_id: str) -> str:
    """Stable key per tenant + gateway + gateway txn id (preferred) or merchant order ref."""
    ref = (gw_txn_id or order_ref).strip().lower()
    if not ref:
        raise ValueError("ipn idempotency key requires val_id/tran_id or equivalent")
    sub = tenant_subdomain.strip().lower()
    gw = gateway.strip().lower()
    return f"shopper:ipn:v1:{sub}:{gw}:{ref}"


async def connect_redis(url: str | None) -> Any:
    if not (url or "").strip():
        log.info("Redis disabled (empty redis_url)")
        return None
    try:
        import redis.asyncio as redis

        client = redis.from_url(
            url.strip(),
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=5.0,
        )
        await client.ping()
        log.info("Redis connected for cache / IPN idempotency")
        return client
    except Exception as e:
        log.warning("Redis unavailable (%s); continuing without Redis", e)
        return None


async def close_redis(client: Any) -> None:
    if client is None:
        return
    try:
        await client.aclose()
    except Exception as e:
        log.warning("Redis close: %s", e)


async def ipn_already_processed(client: Any, key: str) -> bool:
    if client is None:
        return False
    return bool(await client.get(key))


async def ipn_record_processed(client: Any, key: str, ttl: int) -> None:
    if client is None or ttl <= 0:
        return
    await client.set(key, "1", ex=ttl)
