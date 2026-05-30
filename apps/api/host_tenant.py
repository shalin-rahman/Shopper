"""Resolve tenant subdomain from Host (and optional platform root domain). Pure logic for tests."""

from __future__ import annotations

import re


def subdomain_from_host(host: str, *, platform_root_domain: str | None = None) -> str | None:
    if not host:
        return None
    host = host.split(":")[0].strip().lower()
    root = (platform_root_domain or "").strip().lower()
    if root and host.endswith("." + root):
        sub = host[: -(len(root) + 1)]
        return sub or None
    m = re.match(r"^([a-z0-9][a-z0-9-]*)\.localhost$", host)
    if m:
        return m.group(1)
    if host in ("localhost", "api", "127.0.0.1", "testserver", "test"):
        return "demo"
    return None
