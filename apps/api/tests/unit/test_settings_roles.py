"""Every staff role can read tenant settings; only managers and admins can change them."""


def test_cashier_can_read_settings(client, staff_token_headers):
    assert client.get("/v1/tenant/settings", headers=staff_token_headers).status_code == 200


def test_cashier_cannot_change_settings(client, staff_token_headers):
    r = client.patch("/v1/tenant/settings", json={"theme_id": "ruby"}, headers=staff_token_headers)
    assert r.status_code == 403
