"""Signed links for the public checkout page.

Without a signature, anyone who guesses or sees an invoice id can read the
invoice and start a payment on it. Staff create the link; the token binds the
tenant, the invoice and the expiry time.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import UUID

CHECKOUT_LINK_TTL = timedelta(hours=24)


def sign_checkout(tenant_id: UUID, invoice_id: UUID, expires: int, secret: str) -> str:
    message = f"checkout|{tenant_id}|{invoice_id}|{expires}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_checkout(
    tenant_id: UUID,
    invoice_id: UUID,
    token: str | None,
    expires: int | None,
    secret: str,
    now: datetime | None = None,
) -> bool:
    if not token or expires is None:
        return False
    now = now or datetime.now(timezone.utc)
    if expires <= int(now.timestamp()):
        return False
    expected = sign_checkout(tenant_id, invoice_id, expires, secret)
    return hmac.compare_digest(token.encode(), expected.encode())


def new_checkout_link(
    tenant_id: UUID, invoice_id: UUID, secret: str, ttl: timedelta = CHECKOUT_LINK_TTL
) -> tuple[str, int, str]:
    """Return (token, expires, path) for a fresh link."""
    expires = int((datetime.now(timezone.utc) + ttl).timestamp())
    token = sign_checkout(tenant_id, invoice_id, expires, secret)
    return token, expires, f"/checkout/{invoice_id}?t={token}&e={expires}"
