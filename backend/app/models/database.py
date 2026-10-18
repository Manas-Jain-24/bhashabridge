import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError
from app.core.config import settings

logger = logging.getLogger("bhashabridge.database")

def create_resilient_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})

    # PostgreSQL setup
    try:
        pg_engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2}
        )
        # Verify connection
        with pg_engine.connect() as conn:
            pass
        logger.info("[*] Successfully connected to PostgreSQL database.")
        return pg_engine
    except Exception as e:
        logger.warning(
            f"[!] PostgreSQL at {db_url} is unreachable. "
            "Falling back to local SQLite (sqlite:///./bhashabridge.db) for development."
        )
        return create_engine("sqlite:///./bhashabridge.db", connect_args={"check_same_thread": False})

engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

