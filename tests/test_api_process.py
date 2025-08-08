"""
Tests for Task #201: POST /api/v1/process endpoint.
"""

from fastapi.testclient import TestClient


def test_process_creates_task_and_returns_202(client: TestClient):
    payload = {
        "url": "https://example.com",
        "prompt": "Extract headlines"
    }
    resp = client.post("/api/v1/process", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert "task_id" in data and isinstance(data["task_id"], str) and data["task_id"]
    assert data["status"] == "PENDING"
    assert data["message"].lower().startswith("task created")
