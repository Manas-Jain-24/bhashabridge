import os
import sys
import logging
from typing import Tuple, Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import Engine
from pathlib import Path
from app.core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "bhashabridge.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

logger = logging.getLogger("bhashabridge.database")

active_db_type = "sqlite"

def resolve_database_url(url: Optional[str] = None) -> str:
    """
    Resolves database URL, ensuring default/relative SQLite targets project root deterministically
    regardless of process current working directory.
    """
    db_url = url or settings.DATABASE_URL
    if db_url.startswith("sqlite:///./") or db_url == "sqlite:///bhashabridge.db":
        return DEFAULT_SQLITE_URL
    return db_url

def create_resilient_engine() -> Tuple[Engine, str]:
    global active_db_type
    is_testing = (
        getattr(settings, "TESTING", False)
        or os.getenv("TESTING", "").lower() in ("true", "1")
        or "pytest" in sys.modules
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )
    if is_testing:
        active_db_type = "sqlite"
        return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}), active_db_type

    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///./") or db_url == "sqlite:///bhashabridge.db":
        db_url = DEFAULT_SQLITE_URL
    if db_url.startswith("sqlite"):
        active_db_type = "sqlite"
        return create_engine(db_url, connect_args={"check_same_thread": False}), active_db_type

    # PostgreSQL setup with automatic fallback to SQLite
    try:
        pg_engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2}
        )
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[*] Successfully connected to PostgreSQL database.")
        active_db_type = "postgresql"
        return pg_engine, active_db_type
    except Exception as e:
        if not settings.ALLOW_SQLITE_FALLBACK:
            raise RuntimeError("Configured database is unavailable. SQLite fallback is disabled.") from e
        logger.warning(
            f"[!] PostgreSQL at configured URL is unreachable ({e}). "
            "Falling back to local SQLite (sqlite:///./bhashabridge.db) for development."
        )
        active_db_type = "sqlite_fallback"
        return create_engine(DEFAULT_SQLITE_URL, connect_args={"check_same_thread": False}), active_db_type

engine, active_db_type = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Module reloads (used by the configuration regression test) must keep the
# mapped classes and metadata attached to the same declarative base.
Base = globals().get("Base") or declarative_base()

def init_db(target_engine: Engine = None, seed: bool = True):
    """Initializes tables and default seed data without import-time side effects."""
    eng = target_engine or engine
    import app.models.entities  # ensures models are registered
    Base.metadata.create_all(bind=eng)
    if seed:
        from app.models.seed import seed_database
        SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=eng)
        with SessionMaker() as db_session:
            seed_database(db_session)

def check_db_health(target_engine: Engine = None) -> Dict[str, Any]:
    """Safely checks database availability without leaking credentials."""
    eng = target_engine or engine
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "type": active_db_type
        }
    except Exception as exc:
        return {
            "status": "error",
            "type": active_db_type,
            "error": str(exc.__class__.__name__)
        }

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

