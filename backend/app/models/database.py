import os
import sys
import logging
from typing import Tuple, Dict, Any, Optional
from sqlalchemy import create_engine, event, text
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


def enable_sqlite_constraints(eng: Engine) -> None:
    if eng.dialect.name == "sqlite" and not event.contains(eng, "connect", _sqlite_foreign_keys):
        event.listen(eng, "connect", _sqlite_foreign_keys)


def _sqlite_foreign_keys(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")


def sqlite_engine(url):
    eng = create_engine(url, connect_args={"check_same_thread": False, "timeout": 5})
    enable_sqlite_constraints(eng)
    return eng

def create_resilient_engine() -> Tuple[Engine, str]:
    global active_db_type
    is_testing = (
        getattr(settings, "TESTING", False)
        or os.getenv("TESTING", "").lower() in ("true", "1")
        or "pytest" in sys.modules
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )
    if is_testing and settings.APP_ENV != "production":
        active_db_type = "sqlite"
        return sqlite_engine("sqlite:///:memory:"), active_db_type

    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///./") or db_url == "sqlite:///bhashabridge.db":
        db_url = DEFAULT_SQLITE_URL
    if db_url.startswith("sqlite"):
        active_db_type = "sqlite"
        return sqlite_engine(db_url), active_db_type

    # PostgreSQL setup with automatic fallback to SQLite
    try:
        pg_engine = create_engine(
            db_url,
            pool_size=8,
            max_overflow=4,
            pool_timeout=3,
            pool_pre_ping=True,
            hide_parameters=True,
            connect_args={"connect_timeout": 3, "options": "-c timezone=UTC -c statement_timeout=10000 -c lock_timeout=4000"}
        )
        if settings.APP_ENV != "production" and settings.ALLOW_SQLITE_FALLBACK:
            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        active_db_type = "postgresql"
        return pg_engine, active_db_type
    except Exception as e:
        if settings.APP_ENV == "production" or not settings.ALLOW_SQLITE_FALLBACK:
            raise RuntimeError("Configured database engine could not be created.") from None
        logger.warning(
            f"[!] Configured PostgreSQL is unreachable ({type(e).__name__}). "
            "Falling back to local SQLite (sqlite:///./bhashabridge.db) for development."
        )
        active_db_type = "sqlite_fallback"
        return sqlite_engine(DEFAULT_SQLITE_URL), active_db_type

engine, active_db_type = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Module reloads (used by the configuration regression test) must keep the
# mapped classes and metadata attached to the same declarative base.
Base = globals().get("Base") or declarative_base()

def init_db(target_engine: Engine = None, seed: bool = True):
    """Initializes tables and default seed data without import-time side effects."""
    eng = target_engine or engine
    enable_sqlite_constraints(eng)
    import app.models.entities  # ensures models are registered
    from app.models.migrations import migrate
    migrate(eng)
    if seed:
        from app.models.seed import seed_database
        SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=eng)
        with SessionMaker.begin() as db_session:
            if eng.dialect.name == "postgresql":
                db_session.execute(text("SELECT pg_advisory_xact_lock(2144139072)"))
            elif eng.dialect.name == "sqlite":
                db_session.execute(text("BEGIN IMMEDIATE"))
            seed_database(db_session, include_demo=settings.APP_ENV != "production")

def check_db_health(target_engine: Engine = None) -> Dict[str, Any]:
    """Safely checks database availability without leaking credentials."""
    eng = target_engine or engine
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "type": eng.dialect.name if target_engine else active_db_type
        }
    except Exception as exc:
        return {
            "status": "error",
            "type": eng.dialect.name if target_engine else active_db_type,
            "error": str(exc.__class__.__name__)
        }

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

