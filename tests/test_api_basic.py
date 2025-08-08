"""
Basic API smoke tests to validate Task 101-104 readiness.
"""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Intelligent Web Data Aggregator API"
    assert data["version"] == "1.0.0"


def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_openapi(client: TestClient):
    # HTML docs
    assert client.get("/docs").status_code == 200
    # JSON
    r = client.get("/openapi.json")
    assert r.status_code == 200
    j = r.json()
    assert j["info"]["title"] == "Intelligent Web Data Aggregator"
