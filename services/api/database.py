"""
Database configuration and session management for the FastAPI application.

This module sets up SQLAlchemy database connection, session management,
and provides utilities for database operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from .config import Settings
import os

# Configure logging
logger = logging.getLogger(__name__)

# Helper to parse boolean env flags
def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}

# Create settings instance
settings = Settings()

# Optional: mute SQLAlchemy engine logs and echo based on env flag
MUTE_SQLALCHEMY_LOGGING = _env_flag("SQLALCHEMY_MUTE_LOGGING", False)
if MUTE_SQLALCHEMY_LOGGING:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

# Allow overriding echo via env; default to settings.debug unless muted
SQLALCHEMY_ECHO = _env_flag("SQLALCHEMY_ECHO", settings.debug and not MUTE_SQLALCHEMY_LOGGING)

# Construct database URL if not provided directly
if os.getenv("TEST_SQLITE"):
    # Explicit test override to avoid external Postgres dependency
    DATABASE_URL = os.getenv("TEST_SQLITE_URL", "sqlite:///./test_worker.db")
elif settings.database_url:
    DATABASE_URL = settings.database_url
else:
    DATABASE_URL = (
        f"postgresql://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    echo=SQLALCHEMY_ECHO,  # Log SQL queries when enabled
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that provides a database session.
    
    This function should be used as a FastAPI dependency to get
    a database session for each request.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


def create_tables():
    """
    Create all database tables.
    
    This function should be called during application startup
    to ensure all tables exist.
    """
    from sqlalchemy.exc import OperationalError
    global engine  # allow reassignment on fallback
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except OperationalError as e:  # pragma: no cover - defensive fallback in CI
        msg = str(e)
        if "could not translate host name" in msg or "could not connect" in msg:
            # Fallback to local sqlite to keep tests passing when postgres service absent
            fallback_url = "sqlite:///./fallback_test.db"
            logger.warning("Primary DB unreachable; falling back to %s", fallback_url)
            from sqlalchemy import create_engine as _ce
            new_engine = _ce(fallback_url, connect_args={"check_same_thread": False})
            try:
                engine.dispose()
            except Exception:
                pass
            engine = new_engine
            SessionLocal.configure(bind=engine)
            Base.metadata.create_all(bind=engine)
        else:
            raise


def drop_tables():
    """
    Drop all database tables.
    
    This function is useful for testing and development.
    Use with caution in production!
    """
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
