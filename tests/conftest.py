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

# Use in-memory DB to avoid file locking issues
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# if os.path.exists("./test_debug.db"):
#     os.remove("./test_debug.db")


# Create in-memory engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Patch shared.database.connection to use our in-memory engine globally
# This ensures background tasks and other modules use the SAME DB instance
import shared.database.connection
shared.database.connection.engine = engine
shared.database.connection.SessionLocal = TestingSessionLocal

def override_get_db():
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
    # Register user via API to ensure consistency
    client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "password": "testpass",
            "email": "test@example.com"
        }
    )

    # Login to get token
    response = client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
    else:
        # Fallback for debugging - if registration failed due to existing user?
        # But tables are dropped each time...
        print(f"DEBUG: Login failed: {response.text}")

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