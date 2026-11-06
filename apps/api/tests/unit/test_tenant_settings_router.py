"""GET and PATCH /v1/tenant/settings work on the caller's own row in platform.tenant_settings."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException

from routers.settings import get_tenant_settings, update_tenant_settings
from schemas import TenantSettingsUpdate

TENANT = UUID(int=9)


class Settings:
    testing = False


class Conn:
    def __init__(self, row):
        self.row = row
        self.calls = []

    async def fetchrow(self, sql, *args):
        self.calls.append((" ".join(sql.split()), args))
        return self.row


class Tx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class Ctx:
    tenant_id = TENANT
    dedicated_db = None

    def __init__(self, conn, subdomain="demo"):
        self.conn = conn
        self.subdomain = subdomain

    def transaction(self):
        return Tx(self.conn)


def _row():
    now = datetime.now(timezone.utc)
    return {
        "tenant_id": TENANT, "theme_id": "default", "default_language": "bn", "logo_url": None,
        "legal_title_en": "Shop", "legal_title_bn": "Shop", "bin": None,
        "default_vat_rate_pct": 7.5, "module_access": {"pos": True},
        "created_at": now, "updated_at": now,
    }


@pytest.mark.asyncio
async def test_returns_the_row_for_the_callers_tenant():
    conn = Conn(_row())

    out = await get_tenant_settings(Ctx(conn), None, Settings())

    ((sql, args),) = conn.calls
    assert "FROM platform.tenant_settings WHERE tenant_id = $1" in sql
    assert args == (TENANT,)
    assert out.default_language == "bn"
    assert out.default_vat_rate_pct == Decimal("7.5")


@pytest.mark.asyncio
async def test_missing_row_is_404():
    with pytest.raises(HTTPException) as exc:
        await get_tenant_settings(Ctx(Conn(None)), None, Settings())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_no_subdomain_is_400_and_reads_nothing():
    conn = Conn(_row())

    with pytest.raises(HTTPException) as exc:
        await get_tenant_settings(Ctx(conn, subdomain=None), None, Settings())

    assert exc.value.status_code == 400
    assert conn.calls == []


@pytest.mark.asyncio
async def test_module_access_read_as_text_is_parsed():
    # Without a JSONB codec asyncpg hands back the column as a string.
    conn = Conn({**_row(), "module_access": '{"pos": false}'})

    out = await get_tenant_settings(Ctx(conn), None, Settings())

    assert out.module_access == {"pos": False}


@pytest.mark.asyncio
async def test_patch_sets_only_the_sent_fields_for_the_callers_tenant():
    conn = Conn({**_row(), "default_language": "en", "module_access": '{"pos": false}'})

    out = await update_tenant_settings(
        Ctx(conn), TenantSettingsUpdate(default_language="en", module_access={"pos": False}), None, Settings()
    )

    ((sql, args),) = conn.calls
    assert sql.startswith("UPDATE platform.tenant_settings SET default_language = $1, module_access = $2::jsonb WHERE tenant_id = $3")
    assert args == ("en", json.dumps({"pos": False}), TENANT)
    assert out.default_language == "en"
    assert out.module_access == {"pos": False}


@pytest.mark.asyncio
async def test_patch_can_clear_an_optional_field():
    conn = Conn(_row())

    await update_tenant_settings(Ctx(conn), TenantSettingsUpdate(logo_url=None), None, Settings())

    ((sql, args),) = conn.calls
    assert "SET logo_url = $1 WHERE" in sql
    assert args == (None, TENANT)


@pytest.mark.parametrize("field", ["theme_id", "default_language", "default_vat_rate_pct", "module_access"])
@pytest.mark.asyncio
async def test_patch_null_on_a_required_field_is_422(field):
    conn = Conn(_row())

    with pytest.raises(HTTPException) as exc:
        await update_tenant_settings(Ctx(conn), TenantSettingsUpdate(**{field: None}), None, Settings())

    assert exc.value.status_code == 422
    assert field in exc.value.detail
    assert conn.calls == []


@pytest.mark.asyncio
async def test_patch_with_no_row_is_404():
    with pytest.raises(HTTPException) as exc:
        await update_tenant_settings(Ctx(Conn(None)), TenantSettingsUpdate(theme_id="dark"), None, Settings())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_patch_with_empty_body_returns_current_settings():
    conn = Conn(_row())

    out = await update_tenant_settings(Ctx(conn), TenantSettingsUpdate(), None, Settings())

    ((sql, _),) = conn.calls
    assert sql.startswith("SELECT")
    assert out.theme_id == "default"


@pytest.mark.parametrize("body", [{"default_language": "fr"}, {"default_vat_rate_pct": "101"}, {"theme_id": ""}])
def test_patch_schema_rejects_bad_values(body):
    with pytest.raises(ValueError):
        TenantSettingsUpdate(**body)
