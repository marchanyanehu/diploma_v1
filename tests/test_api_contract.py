from fastapi.testclient import TestClient

from services.api.main import app


def test_openapi_contract_paths_present():
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()

    required_paths = [
        "/auth/register",
        "/auth/token",
        "/api/v1/process",
        "/api/v1/status/{task_id}",
        "/api/v1/result/{task_id}",
        "/api/v1/jobs",
    ]

    for path in required_paths:
        assert path in spec.get("paths", {}), f"Missing path in OpenAPI: {path}"

