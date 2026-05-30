"""Staff management — integration test (requires live database)."""
from __future__ import annotations
import os
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.skipif(
    os.getenv("TESTING") == "1",
    reason="Integration test — requires a live database",
)


@pytest.mark.asyncio
async def test_admin_can_create_cashier(async_client: AsyncClient, auth_headers: dict):
    """
    Ensures that a tenant admin can create a new staff member.
    """
    staff_data = {
        "username": "cashier1",
        "password": "password123",
        "full_name": "John Doe",
        "role": "cashier"
    }
    response = await async_client.post("/v1/tenant/staff", json=staff_data, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["username"] == "cashier1"


@pytest.mark.asyncio
async def test_unauthorized_staff_creation(async_client: AsyncClient):
    """
    Ensures that anonymous or non-admin users cannot create staff.
    """
    staff_data = {"username": "hack", "password": "123", "full_name": "Hacker", "role": "admin"}
    response = await async_client.post("/v1/tenant/staff", json=staff_data)
    assert response.status_code == 401  # No token
