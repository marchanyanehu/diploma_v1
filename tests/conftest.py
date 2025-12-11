import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set TESTING flag before importing app to force in-memory rate limiter
os.environ["TESTING"] = "1"

# Ensure repo root is importable (so `services` package resolves)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.main import app, get_db
from shared.database import Base
from services.api import auth
import shared.database as db_utils

# Use file-based DB for debugging
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_debug.db"

if os.path.exists("./test_debug.db"):
    os.remove("./test_debug.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    print(f"DEBUG: override_get_db called. Engine: {engine.url}")
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    print(f"DEBUG: Creating tables. Tables found: {list(Base.metadata.tables.keys())}")
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def auth_client(client):
    """Create an authenticated test client."""
    # Create user
    db = TestingSessionLocal()
    try:
        # Check if user exists first (tests share state sometimes if not properly torn down)
        if not db_utils.get_user_by_username(db, "testuser"):
            # Manually instantiate AuthService to avoid Depends() error
            user_repo = auth.SqlAlchemyUserRepository(db)
            auth_service = auth.AuthService(
                secret_key=auth.SECRET_KEY,
                algorithm=auth.ALGORITHM,
                access_token_expire_minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES,
                user_repo=user_repo
            )
            hashed_password = auth_service.hash_password("testpass")
            db_utils.create_user(db, "testuser", hashed_password, "test@example.com")
    finally:
        db.close()

    # Get token
    # Re-instantiate AuthService for token creation (needs no DB session for encoding)
    # We can pass a dummy repo or None if we trust it doesn't use it for encoding
    # But AuthService.__init__ requires user_repo.
    # Let's just use a fresh session/repo.
    db = TestingSessionLocal()
    try:
        user_repo = auth.SqlAlchemyUserRepository(db)
        auth_service = auth.AuthService(
            secret_key=auth.SECRET_KEY,
            algorithm=auth.ALGORITHM,
            access_token_expire_minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES,
            user_repo=user_repo
        )
        token = auth_service.create_access_token(username="testuser")
    finally:
        db.close()

    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture(scope="session", autouse=True)
def suppress_litellm_logging_errors():
    """Suppress litellm async cleanup logging errors at test teardown."""
    import logging
    import warnings
    
    # Filter out the specific logging error from litellm cleanup
    warnings.filterwarnings("ignore", message=".*Using proactor.*")
    
    # Suppress asyncio event loop warnings during cleanup
    logging.getLogger("asyncio").setLevel(logging.ERROR)
    yield