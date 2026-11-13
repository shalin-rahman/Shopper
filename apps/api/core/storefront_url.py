"""Tenant-specific storefront base URL. The API finds the tenant from the Host, so links need it."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

PLACEHOLDER = "{subdomain}"


def tenant_storefront_url(base: str | None, subdomain: str) -> str:
    """Return the storefront URL for one tenant, without a trailing slash.

    `base` is the root domain, for example https://publicportal.example, and the
    tenant becomes a subdomain of it. If `base` has a {subdomain} placeholder, that
    is replaced instead. An empty `base` gives https://{subdomain}.shopper.com.
    """
    base = (base or "").strip()
    if not base:
        return f"https://{subdomain}.shopper.com"
    if PLACEHOLDER in base:
        return base.replace(PLACEHOLDER, subdomain).rstrip("/")
    if "://" not in base:
        base = "https://" + base
    parts = urlsplit(base)
    return urlunsplit((parts.scheme, f"{subdomain}.{parts.netloc}", parts.path, "", "")).rstrip("/")
