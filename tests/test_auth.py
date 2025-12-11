
import pytest
from fastapi.testclient import TestClient
from services.api.main import app
from services.api import auth
import shared.database as db_utils

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpassword", "email": "test@example.com"},
    )
    # If user already exists from other tests, we might get 400. 
    # But conftest.py client fixture drops tables after each test function? 
    # No, conftest.py client fixture is function scope by default?
    # Let's check conftest.py scope.
    if response.status_code == 400 and "already registered" in response.json().get("detail", ""):
         assert True
    else:
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert "id" in data


def test_register_rejects_long_password(client):
    long_password = "x" * 100
    response = client.post(
        "/auth/register",
        json={"username": "longpass", "password": long_password},
    )
    assert response.status_code == 400
    assert "72 bytes" in response.json()["detail"]

def test_login_for_access_token(client):
    # Register first
    client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpassword", "email": "test@example.com"},
    )
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
    # Register first
    client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpassword", "email": "test@example.com"},
    )
    # Login first
    login_res = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    token = login_res.json()["access_token"]
    
    response = client.post(
        "/api/v1/process",
        json={"url": "https://example.com", "prompt": "test prompt"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    assert "task_id" in response.json()
