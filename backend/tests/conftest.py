import os
import re
import uuid
import shutil
import gc
import hashlib
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient

# Ensure test flags are set BEFORE importing any application modules or services
os.environ["TESTING"] = "true"
os.environ["USE_MOCK_MODELS"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.config import settings
settings.TESTING = True
settings.USE_MOCK_MODELS = True
settings.DATABASE_URL = "sqlite:///:memory:"

from app.main import app
from app.models.database import Base, get_db, init_db

# Project-local, explicit, writable pytest temp directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PYTEST_TMP_DIR = PROJECT_ROOT / ".pytest_tmp"
PYTEST_TMP_DIR.mkdir(parents=True, exist_ok=True)

@pytest.fixture(scope="session", autouse=True)
def verify_production_db_unmodified():
    """
    Guarantees that the real project bhashabridge.db is never touched, created, or mutated by pytest.
    Captures SHA-256 and modification time before the test suite, and verifies they remain unchanged after.
    """
    prod_db = PROJECT_ROOT / "bhashabridge.db"
    backend_db = PROJECT_ROOT / "backend" / "bhashabridge.db"
    backend_snapshot = (backend_db.exists(), backend_db.stat().st_mtime if backend_db.exists() else None,
                        hashlib.sha256(backend_db.read_bytes()).hexdigest() if backend_db.exists() else None)

    initial_exists = prod_db.exists()
    initial_mtime = prod_db.stat().st_mtime if initial_exists else None
    initial_sha256 = (
        hashlib.sha256(prod_db.read_bytes()).hexdigest() if initial_exists else None
    )

    yield {
        "exists": initial_exists,
        "mtime": initial_mtime,
        "sha256": initial_sha256,
        "path": prod_db,
    }

    if initial_exists:
        assert prod_db.exists(), "Production bhashabridge.db was deleted during tests!"
        final_mtime = prod_db.stat().st_mtime
        final_sha256 = hashlib.sha256(prod_db.read_bytes()).hexdigest()
        assert final_mtime == initial_mtime, (
            f"Production bhashabridge.db mtime changed! "
            f"Initial: {initial_mtime}, Final: {final_mtime}"
        )
        assert final_sha256 == initial_sha256, (
            f"Production bhashabridge.db SHA-256 changed! "
            f"Initial: {initial_sha256}, Final: {final_sha256}"
        )
    else:
        assert not prod_db.exists(), "Production bhashabridge.db was created by tests!"
    assert backend_db.exists() == backend_snapshot[0], "Backend database existence changed during tests"
    if backend_snapshot[0]:
        assert backend_db.stat().st_mtime == backend_snapshot[1], "Backend database mtime changed during tests"
        assert hashlib.sha256(backend_db.read_bytes()).hexdigest() == backend_snapshot[2], "Backend database content changed during tests"

@pytest.fixture(scope="function")
def test_engine(request):
    """
    Creates a fresh, isolated temporary SQLite database with seed data for each test.
    Uses a globally unique per-test directory (node name + UUID hex) under .pytest_tmp
    to prevent stale file locks, SQLite concurrency blocks, or permission collisions.
    Uses NullPool so connections close immediately without holding open locks.
    """
    PYTEST_TMP_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w\-_\.]", "_", request.node.name)
    test_id = f"{safe_name}_{uuid.uuid4().hex[:10]}"
    test_dir = PYTEST_TMP_DIR / test_id
    test_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_dir / "test_bhashabridge.db"

    engine = create_engine(
        f"sqlite:///{db_path}",
        poolclass=NullPool,
        connect_args={"check_same_thread": False, "timeout": 15}
    )
    init_db(target_engine=engine, seed=True)
    yield engine
    engine.dispose()

    # Explicit garbage collection to ensure Windows closes any SQLite file handles
    gc.collect()

    # Do not silently ignore failed directory cleanup
    try:
        shutil.rmtree(test_dir, ignore_errors=False)
    except Exception as exc:
        import time
        time.sleep(0.05)
        gc.collect()
        try:
            shutil.rmtree(test_dir, ignore_errors=False)
        except Exception as retry_exc:
            raise RuntimeError(
                f"Failed to clean up test database directory {test_dir}: {retry_exc}"
            ) from retry_exc

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provides a fresh transactional session for direct DB tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(test_engine):
    """Provides a TestClient with get_db overridden to use the isolated test database."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.state.skip_init_db = True
    app.state.db_engine = test_engine
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    app.state.skip_init_db = False
    app.state.db_engine = None
