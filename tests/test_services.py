"""
Comprehensive unit tests for service layer.

Tests TaskService, AuthService, and task_presenter to ensure
proper business logic, error handling, and SOLID principles.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from services.api.services.task_service import (
    TaskService,
    TaskQueue,
    CeleryTaskQueue,
    TaskNotFoundError,
    TaskForbiddenError,
)
from services.api.services.auth_service import AuthService
from services.api.services import task_presenter
from services.api.repositories import TaskRepository
from services.api.schemas import TaskStatus
from shared.database import ScrapingTask, User


class TestTaskService:
    """Unit tests for TaskService."""

    def test_create_task_generates_uuid(self):
        """Test create_task generates valid UUID."""
        # Mock dependencies
        db_mock = Mock()
        queue_mock = Mock(spec=TaskQueue)
        task_repo_mock = Mock(spec=TaskRepository)
        task_repo_mock.create = Mock()
        
        service = TaskService(db=db_mock, queue=queue_mock, task_repo=task_repo_mock)
        
        task_id = service.create_task(
            url="https://example.com",
            prompt="Extract data",
            owner_id=1
        )
        
        # Verify UUID format (36 chars with hyphens)
        assert len(task_id) == 36
        assert task_id.count('-') == 4

    def test_create_task_persists_to_database(self):
        """Test create_task calls repository with correct parameters."""
        db_mock = Mock()
        queue_mock = Mock(spec=TaskQueue)
        task_repo_mock = Mock(spec=TaskRepository)
        
        service = TaskService(db=db_mock, queue=queue_mock, task_repo=task_repo_mock)
        
        task_id = service.create_task(
            url="https://example.com",
            prompt="Extract data",
            owner_id=5
        )
        
        # Verify repository was called
        task_repo_mock.create.assert_called_once()
        call_kwargs = task_repo_mock.create.call_args.kwargs
        assert call_kwargs['task_id'] == task_id
        assert call_kwargs['url'] == "https://example.com"
        assert call_kwargs['user_prompt'] == "Extract data"
        assert call_kwargs['status'] == TaskStatus.PENDING
        assert call_kwargs['owner_id'] == 5

    def test_create_task_enqueues_to_queue(self):
        """Test create_task enqueues work to task queue."""
        db_mock = Mock()
        queue_mock = Mock(spec=TaskQueue)
        task_repo_mock = Mock(spec=TaskRepository)
        task_repo_mock.create = Mock()
        
        service = TaskService(db=db_mock, queue=queue_mock, task_repo=task_repo_mock)
        
        task_id = service.create_task(
            url="https://example.com",
            prompt="Extract data",
            owner_id=1,
            correlation_id="corr-123"
        )
        
        # Verify queue enqueue was called
        queue_mock.enqueue.assert_called_once()
        args = queue_mock.enqueue.call_args
        assert args[0][0] == "scrape.process_request_full"
        assert args[0][1] == [task_id, "https://example.com", "Extract data"]
        assert args[1]['correlation_id'] == "corr-123"

    def test_create_task_handles_db_failure_gracefully(self):
        """Test create_task continues even if DB persist fails."""
        db_mock = Mock()
        queue_mock = Mock(spec=TaskQueue)
        task_repo_mock = Mock(spec=TaskRepository)
        task_repo_mock.create = Mock(side_effect=Exception("DB Error"))
        
        service = TaskService(db=db_mock, queue=queue_mock, task_repo=task_repo_mock)
        
        # Should not raise exception
        task_id = service.create_task(
            url="https://example.com",
            prompt="Extract data",
            owner_id=1
        )
        
        # Should still return task_id
        assert task_id is not None
        # Should still try to enqueue
        queue_mock.enqueue.assert_called_once()

    def test_create_task_handles_queue_failure_gracefully(self):
        """Test create_task logs error if queue fails but doesn't raise."""
        db_mock = Mock()
        queue_mock = Mock(spec=TaskQueue)
        queue_mock.enqueue = Mock(side_effect=Exception("Queue Error"))
        task_repo_mock = Mock(spec=TaskRepository)
        task_repo_mock.create = Mock()
        
        service = TaskService(db=db_mock, queue=queue_mock, task_repo=task_repo_mock)
        
        # Should not raise exception
        task_id = service.create_task(
            url="https://example.com",
            prompt="Extract data",
            owner_id=1
        )
        
        # Should still return task_id
        assert task_id is not None

    def test_get_task_for_user_returns_task_for_owner(self):
        """Test get_task_for_user returns task when user is owner."""
        db_mock = Mock()
        queue_mock = Mock(spec=TaskQueue)
        task_repo_mock = Mock(spec=TaskRepository)
        
        # Mock task owned by user
        mock_task = Mock()
        mock_task.owner_id = 5
        task_repo_mock.get_by_task_id = Mock(return_value=mock_task)
        
        service = TaskService(db=db_mock, queue=queue_mock, task_repo=task_repo_mock)
        
        task = service.get_task_for_user("task-123", owner_id=5)
        
        assert task == mock_task

    def test_get_task_for_user_raises_not_found_if_task_missing(self):
        """Test get_task_for_user raises TaskNotFoundError if task doesn't exist."""
        db_mock = Mock()
        queue_mock = Mock(spec=TaskQueue)
        task_repo_mock = Mock(spec=TaskRepository)
        task_repo_mock.get_by_task_id = Mock(return_value=None)
        
        service = TaskService(db=db_mock, queue=queue_mock, task_repo=task_repo_mock)
        
        with pytest.raises(TaskNotFoundError):
            service.get_task_for_user("nonexistent", owner_id=1)

    def test_get_task_for_user_raises_forbidden_if_wrong_owner(self):
        """Test get_task_for_user raises TaskForbiddenError if user not owner."""
        db_mock = Mock()
        queue_mock = Mock(spec=TaskQueue)
        task_repo_mock = Mock(spec=TaskRepository)
        
        # Mock task owned by different user
        mock_task = Mock()
        mock_task.owner_id = 5
        task_repo_mock.get_by_task_id = Mock(return_value=mock_task)
        
        service = TaskService(db=db_mock, queue=queue_mock, task_repo=task_repo_mock)
        
        with pytest.raises(TaskForbiddenError):
            service.get_task_for_user("task-123", owner_id=999)


class TestCeleryTaskQueue:
    """Unit tests for CeleryTaskQueue."""

    def test_enqueue_sends_task_to_celery(self):
        """Test enqueue calls celery send_task with correct parameters."""
        celery_mock = Mock()
        queue = CeleryTaskQueue(celery_mock, queue_name="test_queue")
        
        queue.enqueue(
            task_name="test.task",
            args=["arg1", "arg2"],
            correlation_id="corr-123"
        )
        
        celery_mock.send_task.assert_called_once_with(
            "test.task",
            args=["arg1", "arg2"],
            queue="test_queue",
            headers={"correlation_id": "corr-123"}
        )

    def test_enqueue_without_correlation_id(self):
        """Test enqueue without correlation_id sends None headers."""
        celery_mock = Mock()
        queue = CeleryTaskQueue(celery_mock)
        
        queue.enqueue(task_name="test.task", args=[])
        
        celery_mock.send_task.assert_called_once()
        call_args = celery_mock.send_task.call_args
        assert call_args.kwargs['headers'] is None


class TestAuthService:
    """Unit tests for AuthService."""

    def test_hash_password_returns_bcrypt_hash(self):
        """Test hash_password returns valid bcrypt hash."""
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        hashed = auth_service.hash_password("mypassword")
        
        # Bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # Bcrypt hash length

    def test_hash_password_different_for_same_password(self):
        """Test hash_password generates different salts each time."""
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        hash1 = auth_service.hash_password("mypassword")
        hash2 = auth_service.hash_password("mypassword")
        
        # Same password should produce different hashes (different salts)
        assert hash1 != hash2

    def test_verify_password_correct_password(self):
        """Test verify_password returns True for correct password."""
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        hashed = auth_service.hash_password("correctpassword")
        result = auth_service.verify_password("correctpassword", hashed)
        
        assert result is True

    def test_verify_password_incorrect_password(self):
        """Test verify_password returns False for incorrect password."""
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        hashed = auth_service.hash_password("correctpassword")
        result = auth_service.verify_password("wrongpassword", hashed)
        
        assert result is False

    def test_create_access_token_contains_username(self):
        """Test create_access_token includes username in payload."""
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        token = auth_service.create_access_token(username="testuser")
        
        # Decode token to verify payload
        import jwt
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "testuser"

    def test_create_access_token_includes_expiry(self):
        """Test create_access_token includes expiry timestamp."""
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        token = auth_service.create_access_token(username="testuser")
        
        # Decode token to verify expiry
        import jwt
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert "exp" in payload
        
        # Verify expiry is in the future
        exp_timestamp = payload["exp"]
        now = datetime.now(timezone.utc).timestamp()
        assert exp_timestamp > now

    def test_create_access_token_custom_expiry(self):
        """Test create_access_token respects custom expiry delta."""
        user_repo_mock = Mock()
        auth_service = AuthService(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            user_repo=user_repo_mock
        )
        
        custom_delta = timedelta(minutes=5)
        token = auth_service.create_access_token(
            username="testuser",
            expires_delta=custom_delta
        )
        
        # Decode and verify expiry
        import jwt
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        exp_timestamp = payload["exp"]
        now = datetime.now(timezone.utc)
        expected_exp = now + custom_delta
        
        # Allow 2 second tolerance
        assert abs(exp_timestamp - expected_exp.timestamp()) < 2


class TestTaskPresenter:
    """Unit tests for task_presenter module."""

    def test_normalize_status_maps_db_status_to_enum(self):
        """Test normalize_status maps database status strings to TaskStatus enum."""
        mock_task = Mock()
        
        # Test PENDING
        mock_task.status = "PENDING"
        assert task_presenter.normalize_status(mock_task) == TaskStatus.PENDING
        
        # Test IN_PROGRESS
        mock_task.status = "IN_PROGRESS"
        assert task_presenter.normalize_status(mock_task) == TaskStatus.IN_PROGRESS
        
        # Test SUCCESS
        mock_task.status = "SUCCESS"
        assert task_presenter.normalize_status(mock_task) == TaskStatus.SUCCESS
        
        # Test FAILED
        mock_task.status = "FAILED"
        assert task_presenter.normalize_status(mock_task) == TaskStatus.FAILED

    def test_build_status_response_pending_task(self):
        """Test build_status_response for PENDING task."""
        mock_task = Mock(spec=ScrapingTask)
        mock_task.task_id = "task-123"
        mock_task.status = "PENDING"
        mock_task.error_message = None
        mock_task.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_task.started_at = None
        mock_task.completed_at = None
        
        response = task_presenter.build_status_response(mock_task)
        
        assert response.task_id == "task-123"
        assert response.status == "PENDING"
        assert response.progress is None or response.progress == 0
        assert response.created_at == mock_task.created_at

    def test_build_status_response_in_progress_task(self):
        """Test build_status_response for IN_PROGRESS task."""
        mock_task = Mock(spec=ScrapingTask)
        mock_task.task_id = "task-123"
        mock_task.status = "IN_PROGRESS"
        mock_task.error_message = None
        mock_task.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_task.started_at = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
        mock_task.completed_at = None
        
        response = task_presenter.build_status_response(mock_task)
        
        assert response.task_id == "task-123"
        assert response.status == "IN_PROGRESS"
        # Progress might be calculated based on time or set to a default
        assert response.progress is None or 0 <= response.progress <= 100

    def test_build_status_response_success_task(self):
        """Test build_status_response for SUCCESS task."""
        mock_task = Mock(spec=ScrapingTask)
        mock_task.task_id = "task-123"
        mock_task.status = "SUCCESS"
        mock_task.error_message = None
        mock_task.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_task.started_at = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
        mock_task.completed_at = datetime(2024, 1, 1, 12, 0, 10, tzinfo=timezone.utc)
        
        response = task_presenter.build_status_response(mock_task)
        
        assert response.task_id == "task-123"
        assert response.status == "SUCCESS"
        assert response.progress == 100

    def test_build_status_response_failed_task(self):
        """Test build_status_response for FAILED task."""
        mock_task = Mock(spec=ScrapingTask)
        mock_task.task_id = "task-123"
        mock_task.status = "FAILED"
        mock_task.error_message = "Timeout error"
        mock_task.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_task.started_at = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
        mock_task.completed_at = datetime(2024, 1, 1, 12, 0, 10, tzinfo=timezone.utc)
        
        response = task_presenter.build_status_response(mock_task)
        
        assert response.task_id == "task-123"
        assert response.status == "FAILED"
        assert response.message == "Timeout error" or "Timeout" in (response.message or "")

    def test_build_result_response_includes_all_fields(self):
        """Test build_result_response includes all required fields."""
        mock_task = Mock(spec=ScrapingTask)
        mock_task.task_id = "task-123"
        mock_task.status = "SUCCESS"
        mock_task.url = "https://example.com"
        mock_task.user_prompt = "Extract data"
        mock_task.extracted_data = [{"text": "Item 1"}, {"text": "Item 2"}]
        mock_task.used_cached_parser = True
        mock_task.total_matches = 2
        mock_task.processing_time_seconds = 5
        mock_task.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_task.completed_at = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
        
        response = task_presenter.build_result_response(mock_task)
        
        assert response.task_id == "task-123"
        assert response.status == "SUCCESS"
        assert response.url == "https://example.com"
        assert response.prompt == "Extract data"
        assert len(response.data) == 2
        assert response.metadata["used_cached_parser"] is True
        assert response.metadata["total_matches"] == 2

    def test_build_result_response_handles_missing_data(self):
        """Test build_result_response handles tasks with missing optional fields."""
        mock_task = Mock(spec=ScrapingTask)
        mock_task.task_id = "task-123"
        mock_task.status = "SUCCESS"
        mock_task.url = "https://example.com"
        mock_task.user_prompt = "Extract data"
        mock_task.extracted_data = None
        mock_task.used_cached_parser = False
        mock_task.total_matches = 0
        mock_task.processing_time_seconds = None
        mock_task.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_task.completed_at = None
        
        response = task_presenter.build_result_response(mock_task)
        
        assert response.task_id == "task-123"
        assert response.data == [] or response.data is None
        assert response.processing_time is None or response.processing_time == 0
