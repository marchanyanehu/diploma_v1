
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpassword", "email": "test@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

def test_login_for_access_token(client):
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_protected_route_without_token(client):
    response = client.post(
        "/api/v1/process",
        json={"url": "https://example.com", "prompt": "test"},
    )
    assert response.status_code == 401

def test_protected_route_with_token(client):
    # Login first
    login_res = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    token = login_res.json()["access_token"]
    
    response = client.post(
        "/api/v1/process",
        json={"url": "https://example.com", "prompt": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    assert "task_id" in response.json()
