"""
Seed data loader for demo/testing mode.

Reads database/full_test_data.json and provides typed helpers
so every router can call `seed.products()`, `seed.customers()` etc.
instead of embedding raw dicts inline.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache
from typing import Any

# Resolve path relative to this file: apps/api/utils/ → database/
_SEED_FILE = Path(__file__).parents[3] / "database" / "full_test_data.json"

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000000"
NOW = datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    with open(_SEED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {t["subdomain"]: t for t in data.get("tenants", [])}


def _tenant(subdomain: str = "demo") -> dict[str, Any]:
    return _load().get(subdomain, _load().get("demo", {}))


# ── Public helpers ─────────────────────────────────────────────────────────

def products(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("products", [])
    result = []
    for i, p in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-0000-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "category_id": None,
            "sku": p["sku"],
            "name_en": p["name_en"],
            "name_bn": p.get("name_bn", ""),
            "description_en": p.get("description_en"),
            "description_bn": p.get("description_bn"),
            "unit": p.get("unit", "pcs"),
            "buy_price": str(p.get("buy_price", "0.00")),
            "sell_price": str(p.get("sell_price", "0.00")),
            "mrp": str(p.get("mrp", p.get("sell_price", "0.00"))),
            "vat_rate_pct": str(p.get("vat_rate_pct", "5.0")),
            "stock_quantity": str(p.get("stock_quantity", 0)),
            "barcode": None,
            "qr_payload": None,
            "is_active": True,
            "created_at": NOW,
            "updated_at": NOW,
        })
    return result


def customers(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("customers", [])
    result = []
    for i, c in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-0001-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "code": f"CUST-{str(i).zfill(3)}",
            "name_en": c["name"],
            "name_bn": c.get("name_bn", c["name"]),
            "phone": c.get("phone"),
            "email": c.get("email"),
            "billing_address_en": c.get("address"),
            "billing_address_bn": c.get("address_bn"),
            "is_credit_allowed": c.get("is_credit_allowed", False),
            "credit_limit": str(c.get("credit_limit", "0")),
            "created_at": NOW,
        })
    return result


def suppliers(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("suppliers", [])
    result = []
    for i, s in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-0005-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "code": f"SUP-{str(i).zfill(3)}",
            "name": s["name"],
            "contact_name": s.get("contact_name"),
            "phone": s.get("phone"),
            "email": s.get("email"),
            "address": s.get("address"),
            "tin": s.get("tin"),
            "created_at": NOW,
        })
    return result


def staff(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("staff", [])
    result = []
    for i, s in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-0006-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "username": s["username"],
            "full_name": s.get("full_name", s["username"].replace("_", " ").title()),
            "role": s["role"],
            "email": s.get("email"),
            "is_active": True,
            "created_at": NOW,
        })
    return result


def expenses(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("accounting", {}).get("expenses", [])
    result = []
    for i, e in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-0003-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "category_name": e["category"],
            "amount": str(e["amount"]),
            "description": e.get("notes"),
            "payment_method": e.get("payment_method"),
            "expense_date": NOW[:10],
            "created_at": NOW,
        })
    return result


def accounts(subdomain: str = "demo") -> list[dict]:
    entries = _tenant(subdomain).get("accounting", {}).get("ledger_entries", [])
    seen: dict[str, dict] = {}
    type_map = {"Cash": "asset", "Inventory": "asset", "Accounts Payable": "liability"}
    for e in entries:
        acct = e["account"]
        if acct not in seen:
            seen[acct] = {
                "id": f"00000000-0000-0000-0004-{str(len(seen)+1).zfill(12)}",
                "tenant_id": DEMO_TENANT_ID,
                "code": f"{1000 + len(seen)}",
                "name_en": acct,
                "name_bn": acct,
                "type": type_map.get(acct, "asset"),
                "current_balance": str(e.get("debit", 0) - e.get("credit", 0)),
            }
    return list(seen.values())


def purchase_orders(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("procurement", {}).get("purchase_orders", [])
    result = []
    for i, po in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-0007-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "po_no": po["po_no"],
            "supplier_name": po["supplier_name"],
            "status": po["status"],
            "total_amount": str(po["total_amount"]),
            "amount_paid": str(po["amount_paid"]),
            "balance_due": str(po["balance_due"]),
            "created_at": po.get("created_at", NOW),
        })
    return result


def inventory_adjustments(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("inventory_adjustments", [])
    result = []
    for i, adj in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-0008-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "sku": adj["sku"],
            "quantity": str(adj["quantity"]),
            "type": adj["type"],
            "notes": adj.get("notes"),
            "created_at": adj.get("created_at", NOW),
        })
    return result


def supplier_payments(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("procurement", {}).get("supplier_payments", [])
    result = []
    for i, p in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-0009-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "supplier_id": f"00000000-0000-0000-0005-{str(i).zfill(12)}",
            "po_id": None,
            "payment_no": p.get("payment_no", f"PAY-{1000+i}"),
            "amount": str(p["amount"]),
            "payment_method": p.get("payment_method", "Bank Transfer"),
            "ref_no": p.get("ref_no"),
            "notes": p.get("notes"),
            "created_at": p.get("created_at", NOW),
        })
    return result


def purchase_returns(subdomain: str = "demo") -> list[dict]:
    items = _tenant(subdomain).get("procurement", {}).get("purchase_returns", [])
    result = []
    for i, r in enumerate(items, start=1):
        result.append({
            "id": f"00000000-0000-0000-000a-{str(i).zfill(12)}",
            "tenant_id": DEMO_TENANT_ID,
            "supplier_id": f"00000000-0000-0000-0005-000000000001",
            "po_id": f"00000000-0000-0000-0007-000000000001",
            "note_no": r.get("note_no", f"DN-{i:04d}"),
            "reason": r.get("reason", ""),
            "total_adjustment": str(r.get("total_adjustment", "0.00")),
            "created_at": r.get("created_at", NOW),
        })
    return result

