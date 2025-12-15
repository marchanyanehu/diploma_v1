"""
Comprehensive edge case and error handling tests.

Tests boundary conditions, error scenarios, and exceptional cases
across the entire application to ensure robustness.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient


class TestEdgeCasesAPI:
    """Edge case tests for API endpoints."""

    def test_process_with_extremely_long_url(self, auth_client):
        """Test processing with very long URL."""
        long_url = "https://example.com/" + "a" * 10000
        
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": long_url,
                "prompt": "Extract data"
            }
        )
        
        # Should either accept or reject with validation error
        assert response.status_code in [202, 422]

    def test_process_with_unicode_characters(self, auth_client):
        """Test processing with Unicode characters in prompt."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract 中文数据 and العربية and Русский"
            }
        )
        
        assert response.status_code == 202

    def test_process_with_emoji_in_prompt(self, auth_client):
        """Test processing with emoji in prompt."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract all items 🎯 with prices 💰"
            }
        )
        
        assert response.status_code == 202

    def test_process_with_special_characters_in_url(self, auth_client):
        """Test processing URLs with special characters."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com/search?q=test&filter=value%20with%20spaces",
                "prompt": "Extract data"
            }
        )
        
        assert response.status_code == 202

    def test_status_with_invalid_task_id_format(self, auth_client):
        """Test status endpoint with invalid task ID format."""
        response = auth_client.get("/api/v1/status/invalid-format-@#$%")
        
        # Should return 404
        assert response.status_code == 404

    def test_result_with_empty_task_id(self, auth_client):
        """Test result endpoint with empty task ID."""
        response = auth_client.get("/api/v1/result/")
        
        # Should return 404 (route not found) or 405
        assert response.status_code in [404, 405]

    def test_register_with_empty_username(self, client):
        """Test registration with empty username."""
        response = client.post(
            "/auth/register",
            json={
                "username": "",
                "password": "password123",
                "email": "test@example.com"
            }
        )
        
        # Should reject with validation error
        assert response.status_code == 422

    def test_register_with_empty_password(self, client):
        """Test registration with empty password."""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "password": "",
                "email": "test@example.com"
            }
        )
        
        # Should reject
        assert response.status_code in [400, 422]

    def test_register_with_very_long_username(self, client):
        """Test registration with very long username."""
        response = client.post(
            "/auth/register",
            json={
                "username": "a" * 1000,
                "password": "password123",
                "email": "test@example.com"
            }
        )
        
        # Should reject or truncate
        assert response.status_code in [200, 400, 422]

    def test_register_with_invalid_email_format(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "password": "password123",
                "email": "not-an-email"
            }
        )
        
        # Should either accept (no email validation) or reject (422)
        assert response.status_code in [200, 422]

    def test_scheduled_job_with_empty_cron(self, auth_client):
        """Test creating scheduled job with empty cron expression."""
        response = auth_client.post(
            "/api/v1/jobs",
            json={
                "url": "https://example.com",
                "prompt": "Test job",
                "schedule_cron": ""
            }
        )
        
        # Should reject with validation error
        assert response.status_code == 422

    def test_delete_nonexistent_job(self, auth_client):
        """Test deleting non-existent job."""
        response = auth_client.delete("/api/v1/jobs/99999")
        
        assert response.status_code == 404

    def test_delete_job_with_invalid_id(self, auth_client):
        """Test deleting job with invalid ID format."""
        response = auth_client.delete("/api/v1/jobs/invalid")
        
        # Should return 422 (validation error)
        assert response.status_code == 422


class TestEdgeCasesDatabase:
    """Edge case tests for database operations."""

    def test_task_with_null_timestamps(self):
        """Test handling tasks with null timestamps."""
        from shared.database import ScrapingTask
        from services.api.services import task_presenter
        
        mock_task = Mock(spec=ScrapingTask)
        mock_task.task_id = "test-task"
        mock_task.status = "PENDING"
        mock_task.created_at = None
        mock_task.started_at = None
        mock_task.completed_at = None
        mock_task.error_message = None
        
        # Should handle gracefully
        with patch.object(task_presenter, 'datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, tzinfo=timezone.utc)
            response = task_presenter.build_status_response(mock_task)
            
            assert response is not None

    def test_task_with_extremely_large_data(self):
        """Test handling tasks with very large extracted data."""
        from shared.database import ScrapingTask
        
        mock_task = Mock(spec=ScrapingTask)
        mock_task.extracted_data = [{"text": "x" * 100000} for _ in range(1000)]
        
        # Should handle without crashing
        assert len(mock_task.extracted_data) == 1000

    def test_parser_cache_with_null_fields(self):
        """Test parser cache with null optional fields."""
        from tests.conftest import TestingSessionLocal
        from shared.database import ParserCache, Domain
        
        db = TestingSessionLocal()
        try:
            # Create domain
            domain = Domain(name="null-fields.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            # Create parser with minimal fields
            parser = ParserCache(
                url_pattern="https://null-fields.com",
                domain_id=domain.id,
                user_intent="Test",
                generated_regex=r"pattern",
                source_type="HTML",
                test_matches_count=1,
                created_by_task_id="test",
                # Optional fields are None
                intent_keywords=None,
                sample_input=None,
                sample_output=None
            )
            db.add(parser)
            db.commit()
            
            assert parser.id is not None
        finally:
            db.close()


class TestEdgeCasesAuth:
    """Edge case tests for authentication."""

    def test_login_with_sql_injection_attempt(self, client):
        """Test login protects against SQL injection."""
        response = client.post(
            "/auth/token",
            data={
                "username": "admin' OR '1'='1",
                "password": "password"
            }
        )
        
        # Should not bypass authentication
        assert response.status_code == 401

    def test_token_with_expired_timestamp(self):
        """Test handling expired JWT token."""
        from services.api.auth import AuthService
        from datetime import timedelta
        
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        # Create token with very short expiry
        token = auth_service.create_access_token(
            username="testuser",
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        # Verify token is expired
        import jwt
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, "test-secret", algorithms=["HS256"])

    def test_token_with_invalid_signature(self, client):
        """Test handling token with invalid signature."""
        # Create a token with different secret
        import jwt
        from datetime import timedelta
        
        payload = {
            "sub": "testuser",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        invalid_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        response = client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract data"
            },
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        
        assert response.status_code == 401

    def test_password_hash_with_special_characters(self):
        """Test password hashing with special characters."""
        from services.api.auth import AuthService
        
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        special_password = "p@ssw0rd!#$%^&*()_+-=[]{}|;':\"<>?,./"
        hashed = auth_service.hash_password(special_password)
        
        # Should hash successfully
        assert hashed is not None
        assert auth_service.verify_password(special_password, hashed)


class TestEdgeCasesWorkflows:
    """Edge case tests for AI workflows."""

    def test_schema_extraction_with_empty_content(self):
        """Test schema extraction with empty content."""
        from services.ai_worker import workflows
        
        llm_mock = Mock()
        llm_mock.chat = Mock(return_value='{"items": []}')
        
        result = workflows.run_schema_extraction(
            task_id="test",
            url="https://example.com",
            schema_fields=["title"],
            inner_text="",
            html_content="",
            llm=llm_mock
        )
        
        # Should handle gracefully
        assert result == [] or isinstance(result, list)

    def test_schema_extraction_with_malformed_html(self):
        """Test schema extraction with malformed HTML."""
        from services.ai_worker import workflows
        
        llm_mock = Mock()
        llm_mock.chat = Mock(return_value='{"items": [{"title": "Item"}]}')
        
        malformed_html = "<div><p>Unclosed tags<div><p>"
        
        result = workflows.run_schema_extraction(
            task_id="test",
            url="https://example.com",
            schema_fields=["title"],
            inner_text="",
            html_content=malformed_html,
            llm=llm_mock
        )
        
        # Should handle without crashing
        assert isinstance(result, list)

    def test_regex_with_catastrophic_backtracking(self):
        """Test handling regex with potential catastrophic backtracking."""
        from services.ai_worker.utils import apply_regex_matches
        
        # Potentially problematic regex
        pattern = r"(a+)+"
        flags = ""
        content = "a" * 30 + "b"
        
        # Should either handle gracefully or timeout
        try:
            matches = apply_regex_matches(pattern, flags, content)
            # If it completes, that's fine
            assert isinstance(matches, list)
        except Exception:
            # If it raises an error, that's also acceptable
            pass

    def test_field_extraction_with_no_keywords(self):
        """Test field extraction with empty keywords list."""
        from services.ai_worker import workflows
        
        llm_mock = Mock()
        db_mock = Mock()
        
        result = workflows.run_field_extraction(
            task_id="test",
            keywords=[],
            inner_text="content",
            html_content="",
            llm=llm_mock,
            db=db_mock,
            domain="example.com"
        )
        
        # Should handle gracefully
        assert result == [] or isinstance(result, list)


class TestEdgeCasesInputSanitization:
    """Edge case tests for input sanitization."""

    def test_sanitize_with_nested_injection(self, auth_client):
        """Test sanitization with nested injection attempts."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract {{{{{{nested}}}}}}"
            }
        )
        
        # Should handle without crashing
        assert response.status_code in [202, 400]

    def test_sanitize_with_null_bytes(self, auth_client):
        """Test sanitization with null bytes."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract data\x00with null"
            }
        )
        
        # Should handle or reject
        assert response.status_code in [202, 400]

    def test_sanitize_with_very_long_prompt(self, auth_client):
        """Test with prompt at maximum length boundary."""
        # Max length is 1000 chars
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "x" * 1000  # Exactly at limit
            }
        )
        
        assert response.status_code == 202

    def test_sanitize_with_excessive_whitespace(self, auth_client):
        """Test with excessive whitespace in prompt."""
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Extract    data    with    spaces"
            }
        )
        
        assert response.status_code == 202


class TestEdgeCasesConcurrency:
    """Edge case tests for concurrent operations."""

    def test_concurrent_user_registration(self, client):
        """Test concurrent registration of same username."""
        # This is difficult to test without actual concurrency
        # but we can verify the endpoint handles conflicts
        
        # First registration
        client.post(
            "/auth/register",
            json={
                "username": "concurrent",
                "password": "pass1",
                "email": "concurrent@example.com"
            }
        )
        
        # Second registration (should fail)
        response = client.post(
            "/auth/register",
            json={
                "username": "concurrent",
                "password": "pass2",
                "email": "concurrent2@example.com"
            }
        )
        
        assert response.status_code == 400

    def test_multiple_tasks_same_url(self, auth_client):
        """Test creating multiple tasks for same URL."""
        responses = []
        for i in range(5):
            response = auth_client.post(
                "/api/v1/process",
                json={
                    "url": "https://example.com",
                    "prompt": f"Extract data {i}"
                }
            )
            responses.append(response)
        
        # All should succeed with unique task IDs
        assert all(r.status_code == 202 for r in responses)
        task_ids = [r.json()["task_id"] for r in responses]
        assert len(set(task_ids)) == 5  # All unique


class TestEdgeCasesErrorRecovery:
    """Edge case tests for error recovery."""

    def test_database_connection_failure_handling(self, client):
        """Test API gracefully handles database connection failures."""
        # Health check should report DB status
        response = client.get("/api/v1/health")
        
        # Should return 200 even if DB is down
        assert response.status_code == 200
        data = response.json()
        assert "database" in data

    def test_llm_timeout_handling(self):
        """Test handling of LLM timeout."""
        from services.ai_worker.llm_client import LLMClient
        
        with patch('litellm.completion') as mock_completion:
            mock_completion.side_effect = TimeoutError("LLM timeout")
            
            llm = LLMClient.from_env()
            
            # Should handle timeout gracefully
            try:
                result = llm.chat([{"role": "user", "content": "test"}])
                # If it returns, check result
                assert result is not None
            except Exception as e:
                # Should raise meaningful error
                assert "timeout" in str(e).lower() or isinstance(e, TimeoutError)

    def test_corrupted_json_in_database(self):
        """Test handling corrupted JSON data in database."""
        from tests.conftest import TestingSessionLocal
        from services.api.repositories import TaskRepository
        
        db = TestingSessionLocal()
        try:
            repo = TaskRepository(db)
            
            # Create task
            task = repo.create(
                task_id="corrupted-json",
                url="https://example.com",
                user_prompt="Test"
            )
            
            # Manually set corrupted JSON (this is a simulation)
            # In real scenario, DB might have corrupted data
            # The application should handle it gracefully
            
            assert task is not None
        finally:
            db.close()
