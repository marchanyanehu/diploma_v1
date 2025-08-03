"""
Test suite for the FastAPI application.

This module contains basic tests to verify the FastAPI application
is properly initialized and basic endpoints are working.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

# Create test client
client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns correct information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Intelligent Web Data Aggregator API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "operational"
    assert "timestamp" in data
    assert data["documentation"] == "/docs"
    assert data["health_check"] == "/health"


def test_health_check_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


def test_api_v1_health_check():
    """Test the API v1 health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "v1"
    assert data["status"] == "healthy"
    assert "endpoints" in data
    assert data["endpoints"]["process"] == "/api/v1/process"
    assert data["endpoints"]["status"] == "/api/v1/status/{task_id}"
    assert data["endpoints"]["result"] == "/api/v1/result/{task_id}"


def test_404_error_handler():
    """Test that 404 errors are handled properly."""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "Not Found"
    assert data["message"] == "The requested resource was not found"
    assert "timestamp" in data


def test_openapi_docs():
    """Test that OpenAPI documentation is available."""
    response = client.get("/docs")
    assert response.status_code == 200
    
    # Test OpenAPI JSON
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_data = response.json()
    assert openapi_data["info"]["title"] == "Intelligent Web Data Aggregator"
    assert openapi_data["info"]["version"] == "1.0.0"


def test_cors_headers():
    """Test that CORS headers are properly set."""
    response = client.options("/")
    assert response.status_code == 200
    # Note: In a real test, you'd check for specific CORS headers
    # This is a basic test to ensure the endpoint responds to OPTIONS
