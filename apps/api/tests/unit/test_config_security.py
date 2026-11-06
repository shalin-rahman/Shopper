import pytest
from fastapi import HTTPException

from core.config import DEFAULT_DEV_JWT_SECRET, Settings
from routers.admin import _require_admin

STRONG = "x" * 32


def _settings(**overrides):
    return Settings(_env_file=None, **overrides)


def test_default_jwt_secret_rejected_outside_testing():
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        _settings(testing=False, jwt_secret_key=DEFAULT_DEV_JWT_SECRET).assert_safe_for_runtime()


def test_empty_jwt_secret_rejected():
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        _settings(testing=False, jwt_secret_key="").assert_safe_for_runtime()


def test_short_jwt_secret_rejected():
    with pytest.raises(RuntimeError, match="32"):
        _settings(testing=False, jwt_secret_key="x" * 31).assert_safe_for_runtime()


def test_strong_secret_accepted():
    _settings(testing=False, jwt_secret_key=STRONG).assert_safe_for_runtime()


def test_testing_mode_allows_default():
    _settings(testing=True, jwt_secret_key=DEFAULT_DEV_JWT_SECRET).assert_safe_for_runtime()


def test_require_admin_rejects_wrong_key():
    with pytest.raises(HTTPException) as exc:
        _require_admin("wrong", _settings(shopper_admin_api_key="right-key"))
    assert exc.value.status_code == 401


def test_require_admin_rejects_missing_key():
    with pytest.raises(HTTPException) as exc:
        _require_admin(None, _settings(shopper_admin_api_key="right-key"))
    assert exc.value.status_code == 401


def test_require_admin_accepts_right_key():
    _require_admin("right-key", _settings(shopper_admin_api_key="right-key"))
