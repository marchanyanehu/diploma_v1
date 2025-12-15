"""
Contract and snapshot testing for API stability.

Tests API contracts to ensure backwards compatibility and uses
snapshot testing to detect unintended changes in responses.
"""

import pytest
import json
from fastapi.testclient import TestClient
from datetime import datetime


class TestAPIContracts:
    """Contract tests to ensure API stability."""

    def test_process_endpoint_contract(self, auth_client):
        """Test /api/v1/process endpoint contract."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract data"
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        
        # Verify contract: required fields
        assert "task_id" in data
        assert "status" in data
        assert "message" in data
        
        # Verify types
        assert isinstance(data["task_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)
        
        # Verify status is valid
        assert data["status"] in ["PENDING", "IN_PROGRESS", "SUCCESS", "FAILED"]

    def test_status_endpoint_contract(self, auth_client):
        """Test /api/v1/status/{task_id} endpoint contract."""
        # Create task first
        create_response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Contract test"
            }
        )
        task_id = create_response.json()["task_id"]
        
        # Check status
        response = auth_client.get(f"/api/v1/status/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify contract: required fields
        assert "task_id" in data
        assert "status" in data
        assert "created_at" in data
        assert "updated_at" in data
        
        # Verify types
        assert isinstance(data["task_id"], str)
        assert isinstance(data["status"], str)
        
        # Verify timestamps are ISO format
        datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))
        
        # Optional fields
        if "progress" in data:
            assert isinstance(data["progress"], (int, type(None)))
            if data["progress"] is not None:
                assert 0 <= data["progress"] <= 100

    def test_result_endpoint_contract_success(self, auth_client):
        """Test /api/v1/result/{task_id} endpoint contract for success."""
        # For this test, we'll test the contract structure
        # even though the task may not be complete
        create_response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Result contract test"
            }
        )
        task_id = create_response.json()["task_id"]
        
        response = auth_client.get(f"/api/v1/result/{task_id}")
        
        # Could be 200 (success), 202 (pending), or 400 (failed)
        assert response.status_code in [200, 202, 400]
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify contract for successful result
            assert "task_id" in data
            assert "status" in data
            assert "url" in data
            assert "prompt" in data
            assert "data" in data
            assert "metadata" in data
            
            # Verify types
            assert isinstance(data["data"], list)
            assert isinstance(data["metadata"], dict)

    def test_register_endpoint_contract(self, client):
        """Test /auth/register endpoint contract."""
        response = client.post(
            "/auth/register",
            json={
                "username": "contractuser",
                "password": "password123",
                "email": "contract@example.com"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify contract
            assert "id" in data
            assert "username" in data
            assert "is_active" in data
            
            # Verify types
            assert isinstance(data["id"], int)
            assert isinstance(data["username"], str)
            assert isinstance(data["is_active"], bool)
            
            # Should not expose password
            assert "password" not in data
            assert "hashed_password" not in data

    def test_login_endpoint_contract(self, client):
        """Test /auth/token endpoint contract."""
        # Register user first
        client.post(
            "/auth/register",
            json={
                "username": "logincontract",
                "password": "password123",
                "email": "logincontract@example.com"
            }
        )
        
        # Login
        response = client.post(
            "/auth/token",
            data={
                "username": "logincontract",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify contract
        assert "access_token" in data
        assert "token_type" in data
        
        # Verify types
        assert isinstance(data["access_token"], str)
        assert isinstance(data["token_type"], str)
        assert data["token_type"] == "bearer"

    def test_jobs_list_endpoint_contract(self, auth_client):
        """Test /api/v1/jobs endpoint contract."""
        response = auth_client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify contract: should be a list
        assert isinstance(data, list)
        
        # If there are jobs, verify their structure
        if len(data) > 0:
            job = data[0]
            assert "id" in job
            assert "url" in job
            assert "prompt" in job
            assert "schedule_cron" in job
            assert "created_at" in job

    def test_user_activity_endpoint_contract(self, auth_client):
        """Test /api/v1/users/me/activity endpoint contract."""
        response = auth_client.get("/api/v1/users/me/activity")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify contract
        assert "tasks" in data
        assert "scheduled_jobs" in data
        
        # Verify types
        assert isinstance(data["tasks"], list)
        assert isinstance(data["scheduled_jobs"], list)

    def test_health_endpoint_contract(self, client):
        """Test /api/v1/health endpoint contract."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify contract
        assert "api_version" in data
        assert "status" in data
        assert "database" in data
        assert "endpoints" in data
        
        # Verify database section
        assert "status" in data["database"]
        assert data["database"]["status"] in ["connected", "disconnected"]

    def test_openapi_schema_contract(self, client):
        """Test OpenAPI schema stability."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        # Verify OpenAPI structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Verify critical paths exist
        critical_paths = [
            "/api/v1/process",
            "/api/v1/status/{task_id}",
            "/api/v1/result/{task_id}",
            "/auth/register",
            "/auth/token"
        ]
        
        for path in critical_paths:
            assert path in schema["paths"], f"Missing critical path: {path}"


class TestBackwardsCompatibility:
    """Tests to ensure backwards compatibility."""

    def test_old_client_can_create_task(self, auth_client):
        """Test that old API clients can still create tasks."""
        # Simulate old client with minimal fields
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Backwards compat test"
            }
        )
        
        # Should still work
        assert response.status_code == 202

    def test_new_optional_fields_ignored(self, auth_client):
        """Test that new optional fields are handled gracefully."""
        # Send request with extra fields that might not exist yet
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Test",
                "future_field": "value",  # Extra field
                "another_new_field": 123
            }
        )
        
        # Should either accept (ignoring extra) or reject with 422
        assert response.status_code in [202, 422]

    def test_response_includes_expected_fields(self, auth_client):
        """Test response includes all documented fields."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Field test"
            }
        )
        
        data = response.json()
        
        # These fields should always be present
        mandatory_fields = ["task_id", "status", "message"]
        for field in mandatory_fields:
            assert field in data, f"Missing mandatory field: {field}"


class TestSnapshotTesting:
    """Snapshot tests to detect unintended response changes."""

    def test_health_response_snapshot(self, client):
        """Test health endpoint response structure hasn't changed."""
        response = client.get("/health")
        data = response.json()
        
        # Expected structure snapshot
        expected_keys = {"status", "timestamp", "service", "version", "uptime"}
        actual_keys = set(data.keys())
        
        # Verify structure matches snapshot
        assert expected_keys.issubset(actual_keys), \
            f"Health response structure changed. Missing: {expected_keys - actual_keys}"

    def test_api_health_response_snapshot(self, client):
        """Test API health endpoint response structure."""
        response = client.get("/api/v1/health")
        data = response.json()
        
        # Expected structure
        expected_keys = {
            "api_version", "status", "timestamp", 
            "database", "endpoints"
        }
        actual_keys = set(data.keys())
        
        assert expected_keys.issubset(actual_keys), \
            f"API health structure changed. Missing: {expected_keys - actual_keys}"
        
        # Database section structure
        db_keys = set(data["database"].keys())
        expected_db_keys = {"status", "tasks_count", "parsers_count"}
        assert expected_db_keys.issubset(db_keys)

    def test_error_response_snapshot(self, client):
        """Test error response structure is consistent."""
        response = client.get("/nonexistent-endpoint")
        data = response.json()
        
        # Expected error structure
        expected_keys = {"error", "message", "timestamp"}
        actual_keys = set(data.keys())
        
        assert expected_keys.issubset(actual_keys), \
            "Error response structure changed"

    def test_validation_error_snapshot(self, auth_client):
        """Test validation error structure."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "invalid-url",
                "prompt": "Test"
            }
        )
        
        # FastAPI validation errors have specific structure
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    def test_task_status_response_snapshot(self, auth_client):
        """Test task status response structure."""
        # Create task
        create_response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Snapshot test"
            }
        )
        task_id = create_response.json()["task_id"]
        
        # Get status
        response = auth_client.get(f"/api/v1/status/{task_id}")
        data = response.json()
        
        # Expected structure
        expected_keys = {
            "task_id", "status", "created_at", "updated_at"
        }
        actual_keys = set(data.keys())
        
        assert expected_keys.issubset(actual_keys), \
            "Task status response structure changed"


class TestAPIVersioning:
    """Tests for API versioning strategy."""

    def test_api_version_in_url(self, client):
        """Test API version is included in URL."""
        # All API endpoints should have /api/v1/ prefix
        response = client.get("/openapi.json")
        schema = response.json()
        
        api_paths = [p for p in schema["paths"] if p.startswith("/api/")]
        
        # All API paths should include version
        for path in api_paths:
            assert path.startswith("/api/v1/"), \
                f"API path missing version: {path}"

    def test_api_version_in_response_header(self, client):
        """Test API version can be determined from response."""
        response = client.get("/api/v1/health")
        data = response.json()
        
        # Version should be in response
        assert "api_version" in data
        assert data["api_version"] == "v1"


class TestSchemaValidation:
    """Tests to ensure schemas are properly validated."""

    def test_scrape_request_schema_validation(self, auth_client):
        """Test ScrapeRequest schema validation."""
        # Test with invalid URL
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "not-a-url",
                "prompt": "Test"
            }
        )
        assert response.status_code == 422
        
        # Test with missing prompt
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com"
            }
        )
        assert response.status_code == 422
        
        # Test with prompt too short
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Hi"  # Less than 5 chars
            }
        )
        assert response.status_code == 422

    def test_user_create_schema_validation(self, client):
        """Test UserCreate schema validation."""
        # Test with missing username
        response = client.post(
            "/auth/register",
            json={
                "password": "password123",
                "email": "test@example.com"
            }
        )
        assert response.status_code == 422
        
        # Test with missing password
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com"
            }
        )
        assert response.status_code == 422

    def test_scheduled_job_schema_validation(self, auth_client):
        """Test ScheduledJobCreate schema validation."""
        # Test with missing cron
        response = auth_client.post(
            "/api/v1/jobs",
            json={
                "url": "https://example.com",
                "prompt": "Test job"
            }
        )
        assert response.status_code == 422
        
        # Test with invalid URL
        response = auth_client.post(
            "/api/v1/jobs",
            json={
                "url": "not-a-url",
                "prompt": "Test job",
                "schedule_cron": "0 * * * *"
            }
        )
        assert response.status_code == 422


class TestResponseConsistency:
    """Tests to ensure response formats are consistent."""

    def test_timestamp_format_consistency(self, auth_client):
        """Test all timestamps use same format."""
        # Create task
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Timestamp test"
            }
        )
        task_id = response.json()["task_id"]
        
        # Get status
        status_response = auth_client.get(f"/api/v1/status/{task_id}")
        status_data = status_response.json()
        
        # All timestamps should be ISO 8601 format
        timestamp_fields = ["created_at", "updated_at"]
        for field in timestamp_fields:
            if field in status_data:
                ts = status_data[field]
                # Should be parseable as ISO format
                datetime.fromisoformat(ts.replace('Z', '+00:00'))

    def test_error_format_consistency(self, client):
        """Test all errors use same format."""
        # Test 404
        response_404 = client.get("/nonexistent")
        data_404 = response_404.json()
        
        # Test 401
        response_401 = client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Test"
            }
        )
        
        # Both should have similar structure
        assert "error" in data_404 or "detail" in data_404
        if response_401.status_code == 401:
            data_401 = response_401.json()
            assert "detail" in data_401 or "error" in data_401

    def test_success_response_consistency(self, auth_client):
        """Test successful responses have consistent structure."""
        # Multiple endpoints should have consistent success structure
        responses = []
        
        # Process endpoint
        resp1 = auth_client.post(
            "/api/v1/process",
            json={"url": "https://example.com", "prompt": "Test 1"}
        )
        responses.append(resp1.json())
        
        # All success responses should be JSON
        for response_data in responses:
            assert isinstance(response_data, dict)
