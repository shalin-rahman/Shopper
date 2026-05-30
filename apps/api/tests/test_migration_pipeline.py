"""Migration pipeline and schema structure tests."""
import os
import pytest
from pathlib import Path

# When running inside Docker at /app/tests/, the repo root is not accessible.
# Try to locate the database directory relative to the API source.
_API_DIR = Path(__file__).resolve().parent.parent          # /app
_REPO_ROOT = _API_DIR.parent.parent                        # repo root (host only)
_DOCKER_MIGRATIONS = Path("/migrations")                   # mounted in docker-compose


def _find_database_dir() -> Path | None:
    """Find the database directory in either host or Docker context."""
    host_db = _REPO_ROOT / "database"
    if host_db.is_dir():
        return host_db
    # In Docker the migrations volume is mounted at /migrations
    if _DOCKER_MIGRATIONS.is_dir():
        return _DOCKER_MIGRATIONS.parent  # won't have full structure
    return None


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Requires DATABASE_URL for migration test")
def test_migration_run():
    """
    Verifies that the migration script can run without errors against the current database.
    """
    import subprocess

    migration_script = _REPO_ROOT / "database" / "run_migrations.py"
    if not migration_script.exists():
        pytest.skip("Migration script not found (running inside Docker?)")

    r = subprocess.run(
        ["python", str(migration_script)],
        capture_output=True,
        text=True,
        env=os.environ
    )
    assert r.returncode == 0
    assert "migrations: done" in r.stdout or "skip" in r.stdout


def test_base_schema_exists():
    """Checks for the presence of the base schema file."""
    db_dir = _find_database_dir()
    if db_dir is None:
        pytest.skip("Database directory not found (running inside Docker container)")

    base_schema = db_dir / "init" / "01_schema_rls.sql"
    if not base_schema.exists():
        pytest.skip("Schema file not accessible from this context")

    assert base_schema.stat().st_size > 0


def test_migration_order():
    """Ensures migration files are named with sequential numbers."""
    # Try host path first, then Docker mount
    migration_dir = _REPO_ROOT / "database" / "migrations"
    if not migration_dir.is_dir():
        migration_dir = _DOCKER_MIGRATIONS
    if not migration_dir.is_dir():
        pytest.skip("Migrations directory not accessible")

    files = list(migration_dir.glob("*.sql"))
    filenames = sorted([f.name for f in files])

    for idx, name in enumerate(filenames):
        version = int(name.split('_')[0])
        assert version >= 2
        if idx > 0:
            prev_version = int(filenames[idx-1].split('_')[0])
            assert version > prev_version, f"Migration {name} is out of order"
