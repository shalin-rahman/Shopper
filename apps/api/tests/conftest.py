import os

import pytest

# Ensure app lifespan skips DB before `main` is imported by test modules.
os.environ["TESTING"] = "1"


@pytest.fixture(autouse=True)
def _fresh_settings_cache():
    """Admin tests mutate env; invalidate cached Settings between cases."""
    from config import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()
