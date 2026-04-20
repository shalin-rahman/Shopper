import pytest
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent

@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Requires DATABASE_URL for migration test")
def test_migration_run():
    """
    Verifies that the migration script can run without errors against the current database.
    In a real CI, this would run against a temporary clean database.
    """
    migration_script = ROOT / "database" / "run_migrations.py"
    assert migration_script.exists()

    # Run the migration script
    # We use the current environment's database
    r = subprocess.run(
        ["python", str(migration_script)],
        capture_output=True,
        text=True,
        env=os.environ
    )
    
    # It should either succeed or report that migrations are already applied
    assert r.returncode == 0
    assert "migrations: done" in r.stdout or "skip" in r.stdout

def test_base_schema_exists():
    """Checks for the presence of the base schema file."""
    base_schema = ROOT / "database" / "init" / "01_schema_rls.sql"
    assert base_schema.exists()
    assert base_schema.stat().st_size > 0

def test_migration_order():
    """Ensures migration files are named with sequential numbers."""
    migration_dir = ROOT / "database" / "migrations"
    files = list(migration_dir.glob("*.sql"))
    filenames = sorted([f.name for f in files])
    
    for idx, name in enumerate(filenames):
        # Starts from 002
        version = int(name.split('_')[0])
        assert version >= 2
        if idx > 0:
            prev_version = int(filenames[idx-1].split('_')[0])
            assert version > prev_version, f"Migration {name} is out of order"
