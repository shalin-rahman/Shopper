"""SKU-linked barcode string and storefront QR payload (label printing / POS)."""

from __future__ import annotations

import re
from urllib.parse import quote

_ALNUM = re.compile(r"[^A-Za-z0-9]+")


def barcode_for_sku(sku: str) -> str:
    """1D-friendly payload (e.g. Code128); strip non-alphanumerics, fallback to digits from hash."""
    s = _ALNUM.sub("", (sku or "").strip())
    if 4 <= len(s) <= 48:
        return s
    h = abs(hash(sku)) % 10**12
    return f"SK{h:012d}"


def qr_payload_for_product(storefront_base: str, subdomain: str, sku: str) -> str:
    base = (storefront_base or "").rstrip("/")
    if not base:
        base = "https://publicportal.example"
    safe_sku = quote(sku, safe="")
    return f"{base}/{subdomain}/p/{safe_sku}"
