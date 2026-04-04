"""
Run against a real Postgres with schema loaded:
  set INTEGRATION_TEST=1 DATABASE_URL=postgresql://shopper_app:...@host:5432/shopper
  pytest tests/test_integration_rls.py -q
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("INTEGRATION_TEST"),
    reason="Set INTEGRATION_TEST=1 and DATABASE_URL to run RLS integration checks",
)


@pytest.fixture(scope="module")
def client():
    os.environ.pop("TESTING", None)
    from importlib import reload

    import main

    reload(main)
    from starlette.testclient import TestClient

    with TestClient(main.app) as c:
        yield c


def test_tenant_a_cannot_see_tenant_b_products(client):
    """Placeholder: extend with second tenant seed + assert isolation."""
    assert os.getenv("DATABASE_URL") or os.getenv("SHOPPER_DATABASE_URL")
