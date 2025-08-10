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

# Configure logging
logger = logging.getLogger(__name__)

# Create settings instance
settings = Settings()

# Construct database URL if not provided directly
if settings.database_url:
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
    echo=settings.debug,  # Log SQL queries in debug mode
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
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables():
    """
    Drop all database tables.
    
    This function is useful for testing and development.
    Use with caution in production!
    """
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
