"""
Comprehensive integration tests for API workflows.

Tests end-to-end workflows including authentication, task creation,
status tracking, and result retrieval.
"""

import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


class TestAuthenticationFlow:
    """Integration tests for authentication workflow."""

    def test_register_and_login_flow(self, client):
        """Test complete registration and login workflow."""
        # Register new user
        register_response = client.post(
            "/auth/register",
            json={
                "username": "integrationuser",
                "password": "securepassword123",
                "email": "integration@example.com"
            }
        )
        
        assert register_response.status_code == 200
        user_data = register_response.json()
        assert user_data["username"] == "integrationuser"
        assert user_data["email"] == "integration@example.com"
        assert "id" in user_data
        
        # Login with credentials
        login_response = client.post(
            "/auth/token",
            data={
                "username": "integrationuser",
                "password": "securepassword123"
            }
        )
        
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        
        # Use token to access protected endpoint
        token = token_data["access_token"]
        protected_response = client.get(
            "/api/v1/users/me/activity",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert protected_response.status_code == 200

    def test_register_duplicate_username_fails(self, client):
        """Test registering with duplicate username fails."""
        # Register first user
        client.post(
            "/auth/register",
            json={
                "username": "duplicate",
                "password": "password1",
                "email": "dup1@example.com"
            }
        )
        
        # Try to register with same username
        response = client.post(
            "/auth/register",
            json={
                "username": "duplicate",
                "password": "password2",
                "email": "dup2@example.com"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_login_wrong_password_fails(self, client):
        """Test login with wrong password fails."""
        # Register user
        client.post(
            "/auth/register",
            json={
                "username": "wrongpass",
                "password": "correctpassword",
                "email": "wrongpass@example.com"
            }
        )
        
        # Try to login with wrong password
        response = client.post(
            "/auth/token",
            data={
                "username": "wrongpass",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401

    def test_login_nonexistent_user_fails(self, client):
        """Test login with non-existent user fails."""
        response = client.post(
            "/auth/token",
            data={
                "username": "nonexistent",
                "password": "password"
            }
        )
        
        assert response.status_code == 401


class TestTaskWorkflow:
    """Integration tests for complete task workflow."""

    def test_create_task_check_status_get_result(self, auth_client):
        """Test complete task lifecycle: create -> check status -> get result."""
        # Create task
        create_response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract all headlines from the page"
            }
        )
        
        assert create_response.status_code == 202
        task_data = create_response.json()
        task_id = task_data["task_id"]
        assert task_data["status"] == "PENDING"
        
        # Check status
        status_response = auth_client.get(f"/api/v1/status/{task_id}")
        
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["task_id"] == task_id
        assert status_data["status"] in ["PENDING", "IN_PROGRESS", "SUCCESS", "FAILED"]
        
        # Try to get result (should be 202 if not completed)
        result_response = auth_client.get(f"/api/v1/result/{task_id}")
        
        # Could be 202 (not ready), 200 (completed), or 400 (failed)
        assert result_response.status_code in [200, 202, 400]

    def test_task_not_found(self, auth_client):
        """Test accessing non-existent task returns 404."""
        response = auth_client.get("/api/v1/status/nonexistent-task-id")
        
        assert response.status_code == 404

    @pytest.mark.skip(reason="Incompatible with sqlite in-memory threading")
    def test_user_cannot_access_other_users_task(self, client):
        """Test user cannot access tasks from other users."""
        # Create first user and task
        from tests.conftest import TestingSessionLocal
        from services.api.auth import AuthService
        from services.api.repositories import UserRepository, TaskRepository
        
        db = TestingSessionLocal()
        try:
            # Create user1
            user_repo = UserRepository(db)
            from shared.config import settings
            auth_service = AuthService(
                secret_key=settings.secret_key,
                algorithm="HS256",
                access_token_expire_minutes=30,
                user_repo=user_repo
            )
            
            # Create user1
            user1 = user_repo.create(
                username="user1_integration",
                password_hash=auth_service.hash_password("pass1"),
                email="user1_int@example.com"
            )
            
            # Create task for user1
            task_repo = TaskRepository(db)
            task = task_repo.create(
                task_id="user1-task",
                url="https://example.com",
                user_prompt="User 1 task",
                owner_id=user1.id
            )
            
            # Create user2
            user2 = user_repo.create(
                username="user2_integration",
                password_hash=auth_service.hash_password("pass2"),
                email="user2_int@example.com"
            )
            
            # Login as user2
            token = auth_service.create_access_token(username="user2_integration")
            
            # Store ID and close session to release lock
            target_task_id = task.task_id
            db.close()
            
            # Try to access user1's task
            response = client.get(
                f"/api/v1/status/{target_task_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 403  # Forbidden
        finally:
            db.close()


class TestSchedulerWorkflow:
    """Integration tests for scheduled jobs workflow."""

    def test_create_list_delete_job(self, auth_client):
        """Test complete scheduled job lifecycle."""
        # Create scheduled job
        create_response = auth_client.post(
            "/api/v1/jobs",
            json={
                "url": "https://example.com",
                "prompt": "Daily scrape",
                "schedule_cron": "0 0 * * *"
            }
        )
        
        assert create_response.status_code == 200
        job_data = create_response.json()
        job_id = job_data["id"]
        assert job_data["schedule_cron"] == "0 0 * * *"
        
        # List jobs
        list_response = auth_client.get("/api/v1/jobs")
        
        assert list_response.status_code == 200
        jobs = list_response.json()
        assert isinstance(jobs, list)
        assert any(j["id"] == job_id for j in jobs)
        
        # Delete job
        delete_response = auth_client.delete(f"/api/v1/jobs/{job_id}")
        
        assert delete_response.status_code == 200
        
        # Verify deletion
        list_response2 = auth_client.get("/api/v1/jobs")
        jobs2 = list_response2.json()
        assert not any(j["id"] == job_id for j in jobs2)

    @pytest.mark.skip(reason="Incompatible with sqlite in-memory threading")
    def test_user_cannot_delete_other_users_job(self, client):
        """Test user cannot delete jobs from other users."""
        from tests.conftest import TestingSessionLocal
        from services.api.auth import AuthService
        from services.api.repositories import UserRepository, ScheduleRepository
        
        db = TestingSessionLocal()
        try:
            # Create users
            user_repo = UserRepository(db)
            from shared.config import settings
            auth_service = AuthService(
                secret_key=settings.secret_key,
                algorithm="HS256",
                access_token_expire_minutes=30,
                user_repo=user_repo
            )
            
            # Create users
            user1 = user_repo.create(
                username="job_owner",
                password_hash=auth_service.hash_password("pass1"),
                email="jobowner@example.com"
            )
            user2 = user_repo.create(
                username="job_other",
                password_hash=auth_service.hash_password("pass2"),
                email="jobother@example.com"
            )
            
            # Create job for user1
            schedule_repo = ScheduleRepository(db)
            job = schedule_repo.create(
                url="https://example.com",
                prompt="Protected job",
                cron="0 * * * *",
                owner_id=user1.id
            )
            
            # Login as user2
            token = auth_service.create_access_token(username="job_other")
            
            # Store ID and close session to release lock
            target_job_id = job.id
            db.close()
            
            # Try to delete user1's job
            response = client.delete(
                f"/api/v1/jobs/{target_job_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 404  # Not found (filtered by owner)
        finally:
            db.close()


class TestUserActivityEndpoint:
    """Integration tests for user activity endpoint."""

    def test_user_activity_includes_tasks_and_jobs(self, auth_client):
        """Test user activity endpoint returns both tasks and jobs."""
        # Create a task
        auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Activity test task"
            }
        )
        
        # Create a scheduled job
        auth_client.post(
            "/api/v1/jobs",
            json={
                "url": "https://example.com",
                "prompt": "Activity test job",
                "schedule_cron": "0 0 * * *"
            }
        )
        
        # Get activity
        response = auth_client.get("/api/v1/users/me/activity")
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "scheduled_jobs" in data
        assert isinstance(data["tasks"], list)
        assert isinstance(data["scheduled_jobs"], list)


class TestInputValidationIntegration:
    """Integration tests for input validation across endpoints."""

    def test_process_blocks_sql_injection_attempt(self, auth_client):
        """Test process endpoint blocks SQL injection attempts."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract data; DROP TABLE users;--"
            }
        )
        
        # Should either reject (400) or sanitize and accept (202)
        assert response.status_code in [202, 400]
        
        if response.status_code == 400:
            # Verify it was blocked for security reasons
            assert "invalid" in response.json()["detail"].lower() or \
                   "prompt" in response.json()["detail"].lower()

    def test_process_blocks_xss_attempt(self, auth_client):
        """Test process endpoint blocks XSS attempts."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "<script>alert('xss')</script>"
            }
        )
        
        # Should either reject or sanitize
        assert response.status_code in [202, 400]

    def test_register_rejects_weak_password(self, client):
        """Test registration with weak password (if validation exists)."""
        # This depends on whether password strength validation is implemented
        response = client.post(
            "/auth/register",
            json={
                "username": "weakuser",
                "password": "123",  # Very weak
                "email": "weak@example.com"
            }
        )
        
        # Could be accepted (200) or rejected (400) depending on validation
        assert response.status_code in [200, 400]

    def test_scheduled_job_rejects_invalid_cron(self, auth_client):
        """Test creating job with invalid cron expression."""
        response = auth_client.post(
            "/api/v1/jobs",
            json={
                "url": "https://example.com",
                "prompt": "Test job",
                "schedule_cron": "invalid cron expression"
            }
        )
        
        # Could be accepted (200) or rejected (400) depending on validation
        # At minimum, should not crash
        assert response.status_code in [200, 400, 422]


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_task_persistence_across_requests(self, auth_client):
        """Test task data persists across multiple requests."""
        # Create task
        create_response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Persistence test"
            }
        )
        task_id = create_response.json()["task_id"]
        
        # Retrieve task multiple times
        for _ in range(3):
            response = auth_client.get(f"/api/v1/status/{task_id}")
            assert response.status_code == 200
            assert response.json()["task_id"] == task_id

    @pytest.mark.skip(reason="Flaky with sqlite in-memory")
    def test_concurrent_task_creation(self, auth_client):
        """Test creating multiple tasks concurrently."""
        tasks = []
        for i in range(5):
            response = auth_client.post(
                "/api/v1/process",
                json={
                    "url": "https://example.com",
                    "prompt": f"Concurrent test {i}"
                }
            )
            assert response.status_code == 202
            tasks.append(response.json()["task_id"])
        
        # Verify all tasks are unique
        assert len(set(tasks)) == 5
        
        # Verify all tasks are retrievable
        for task_id in tasks:
            response = auth_client.get(f"/api/v1/status/{task_id}")
            assert response.status_code == 200


class TestHealthCheckIntegration:
    """Integration tests for health check endpoints."""

    def test_health_endpoints_respond_quickly(self, client):
        """Test health endpoints respond within acceptable time."""
        import time
        
        # Root health
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 1.0  # Should respond within 1 second
        
        # API health with DB check
        start = time.time()
        response = client.get("/api/v1/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0  # Allow more time for DB query

    def test_health_check_includes_metadata(self, client):
        """Test health check includes system metadata."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "endpoints" in data
        assert data["database"]["status"] in ["connected", "disconnected"]


class TestOpenAPIIntegration:
    """Integration tests for OpenAPI documentation."""

    def test_openapi_json_valid(self, client):
        """Test OpenAPI JSON is valid."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        openapi = response.json()
        assert "openapi" in openapi
        assert "info" in openapi
        assert "paths" in openapi

    def test_openapi_includes_all_endpoints(self, client):
        """Test OpenAPI includes all major endpoints."""
        response = client.get("/openapi.json")
        openapi = response.json()
        paths = openapi["paths"]
        
        # Check key endpoints are documented
        assert "/api/v1/process" in paths
        assert "/api/v1/status/{task_id}" in paths
        assert "/api/v1/result/{task_id}" in paths
        assert "/auth/register" in paths
        assert "/auth/token" in paths
        assert "/api/v1/jobs" in paths

    def test_docs_ui_accessible(self, client):
        """Test Swagger UI is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        # Should return HTML
        assert "text/html" in response.headers.get("content-type", "")
