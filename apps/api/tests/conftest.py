import os
import pytest
# Ensure app lifespan skips DB before `main` is imported by test modules.
os.environ["TESTING"] = "1"

import jwt
from datetime import datetime, timedelta, timezone
from starlette.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from main import app
from config import get_settings, clear_settings_cache

# Must match auth_router.py / deps.py
_JWT_SECRET = "shopper-dev-secret-change-in-prod"
_JWT_ALGORITHM = "HS256"


def _make_token(role: str = "admin") -> str:
    """Generate a valid JWT for test use."""
    payload = {
        "uid": "00000000-0000-0000-0000-000000000000",
        "tid": "00000000-0000-0000-0000-000000000000",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


@pytest.fixture(autouse=True)
def _fresh_settings_cache():
    """Admin tests mutate env; invalidate cached Settings between cases."""
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="module")
def auth_headers():
    """Default headers simulating an authenticated admin for the demo tenant."""
    return {"X-Shopper-Tenant": "demo", "Authorization": f"Bearer {_make_token('admin')}"}


@pytest.fixture(scope="module")
def admin_token_headers():
    return {"X-Shopper-Tenant": "demo", "Authorization": f"Bearer {_make_token('admin')}"}


@pytest.fixture(scope="module")
def staff_token_headers():
    return {"X-Shopper-Tenant": "demo", "Authorization": f"Bearer {_make_token('cashier')}"}
