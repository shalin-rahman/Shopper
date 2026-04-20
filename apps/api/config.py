"""Central configuration from environment / .env — use get_settings() instead of os.getenv in app code."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    testing: bool = False
    tenant_isolation_mode: str = "rls"  # rls or schema
    integration_test: bool = False
    database_url: str = "postgresql://shopper_app:shopper_app_change_me@localhost:5432/shopper"
    migrate_database_url: str | None = None
    platform_root_domain: str | None = None
    storefront_public_base_url: str | None = None
    cors_allow_origins: str = "*"
    shopper_admin_api_key: str | None = None
    redis_url: str | None = "redis://redis:6379/0"
    redis_ipn_ttl_seconds: int = 86_400  # IPN replay suppression key TTL (seconds); <= 0 falls back to 86400
    sslcommerz_store_id: str | None = None
    sslcommerz_store_password: str | None = None

    @field_validator(
        "migrate_database_url",
        "storefront_public_base_url",
        "shopper_admin_api_key",
        "redis_url",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if v == "":
            return None
        return v

    def cors_origins_list(self) -> list[str]:
        raw = self.cors_allow_origins.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    def normalize_dsn(self, dsn: str) -> str:
        if "+asyncpg" in dsn:
            return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
        return dsn


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
