import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure repo root is importable (so `services` package resolves)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.main import app, get_db
from services.api.database import Base
from services.api import auth, db_utils

# In-memory DB for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
            hashed_password = auth.get_password_hash("testpass")
            db_utils.create_user(db, "testuser", hashed_password, "test@example.com")
    finally:
        db.close()
    
    # Get token
    token = auth.create_access_token(data={"sub": "testuser"})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
