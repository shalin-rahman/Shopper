"""FastAPI dependency aliases — prefer Depends() over calling get_settings() inside route bodies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from config import Settings, get_settings


def configure_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(configure_settings)]
