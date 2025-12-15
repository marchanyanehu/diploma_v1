"""
Comprehensive unit tests for repository layer.

Tests all repository classes to ensure proper data access patterns,
edge cases, and error handling following SOLID principles.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from services.api.repositories import (
    UserRepository,
    TaskRepository,
    ScheduleRepository,
    ParserRepository,
)
from shared.database import User, ScrapingTask, ScheduledJob, ParserCache, Domain
from services.api.schemas import TaskStatus


class TestUserRepository:
    """Unit tests for UserRepository."""

    def test_create_user_success(self, client):
        """Test creating a new user."""
        db = Session(bind=client.app.dependency_overrides[client.app.dependency_overrides].__self__.kw['bind'])
        repo = UserRepository(db)
        
        user = repo.create(
            username="newuser",
            password_hash="hashed_password",
            email="newuser@example.com"
        )
        
        assert user.id is not None
        assert user.username == "newuser"
        assert user.hashed_password == "hashed_password"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.created_at is not None

    def test_get_by_username_exists(self, client):
        """Test retrieving existing user by username."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            repo = UserRepository(db)
            
            # Create user first
            created = repo.create(
                username="existinguser",
                password_hash="hashed",
                email="existing@example.com"
            )
            
            # Retrieve user
            user = repo.get_by_username("existinguser")
            
            assert user is not None
            assert user.id == created.id
            assert user.username == "existinguser"
        finally:
            db.close()

    def test_get_by_username_not_exists(self, client):
        """Test retrieving non-existent user returns None."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            repo = UserRepository(db)
            user = repo.get_by_username("nonexistent")
            assert user is None
        finally:
            db.close()

    def test_create_duplicate_username_raises_error(self, client):
        """Test creating user with duplicate username raises error."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            repo = UserRepository(db)
            
            # Create first user
            repo.create(
                username="duplicate",
                password_hash="hashed1",
                email="dup1@example.com"
            )
            
            # Attempt to create duplicate
            with pytest.raises(Exception):  # SQLAlchemy IntegrityError
                repo.create(
                    username="duplicate",
                    password_hash="hashed2",
                    email="dup2@example.com"
                )
        finally:
            db.close()

    def test_create_user_with_none_email(self, client):
        """Test creating user with None email is allowed."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            repo = UserRepository(db)
            user = repo.create(
                username="noemail",
                password_hash="hashed",
                email=None
            )
            
            assert user.email is None
            assert user.username == "noemail"
        finally:
            db.close()


class TestTaskRepository:
    """Unit tests for TaskRepository."""

    def test_create_task_success(self, client):
        """Test creating a new task."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            repo = TaskRepository(db)
            
            task = repo.create(
                task_id="test-task-123",
                url="https://example.com",
                user_prompt="Extract data",
                status=TaskStatus.PENDING
            )
            
            assert task.id is not None
            assert task.task_id == "test-task-123"
            assert task.url == "https://example.com"
            assert task.user_prompt == "Extract data"
            assert task.status == TaskStatus.PENDING
            assert task.created_at is not None
        finally:
            db.close()

    def test_create_task_with_owner(self, client):
        """Test creating task with owner_id."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create user first
            user_repo = UserRepository(db)
            user = user_repo.create(
                username="taskowner",
                password_hash="hashed",
                email="owner@example.com"
            )
            
            repo = TaskRepository(db)
            task = repo.create(
                task_id="owned-task",
                url="https://example.com",
                user_prompt="Extract data",
                status=TaskStatus.PENDING,
                owner_id=user.id
            )
            
            assert task.owner_id == user.id
        finally:
            db.close()

    def test_get_by_task_id_exists(self, client):
        """Test retrieving task by task_id."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            repo = TaskRepository(db)
            
            # Create task
            created = repo.create(
                task_id="retrieve-me",
                url="https://example.com",
                user_prompt="Test",
                status=TaskStatus.PENDING
            )
            
            # Retrieve task
            task = repo.get_by_task_id("retrieve-me")
            
            assert task is not None
            assert task.id == created.id
            assert task.task_id == "retrieve-me"
        finally:
            db.close()

    def test_get_by_task_id_not_exists(self, client):
        """Test retrieving non-existent task returns None."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            repo = TaskRepository(db)
            task = repo.get_by_task_id("nonexistent-task")
            assert task is None
        finally:
            db.close()

    def test_list_for_owner_returns_user_tasks(self, client):
        """Test listing tasks for specific owner."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create users
            user_repo = UserRepository(db)
            user1 = user_repo.create(username="user1", password_hash="hash1", email="u1@example.com")
            user2 = user_repo.create(username="user2", password_hash="hash2", email="u2@example.com")
            
            # Create tasks for both users
            repo = TaskRepository(db)
            repo.create(task_id="task1", url="https://example.com", user_prompt="T1", owner_id=user1.id)
            repo.create(task_id="task2", url="https://example.com", user_prompt="T2", owner_id=user1.id)
            repo.create(task_id="task3", url="https://example.com", user_prompt="T3", owner_id=user2.id)
            
            # List tasks for user1
            tasks = repo.list_for_owner(user1.id)
            
            assert len(tasks) == 2
            assert all(t.owner_id == user1.id for t in tasks)
        finally:
            db.close()

    def test_list_for_owner_respects_limit(self, client):
        """Test list_for_owner respects limit parameter."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create user
            user_repo = UserRepository(db)
            user = user_repo.create(username="limituser", password_hash="hash", email="limit@example.com")
            
            # Create multiple tasks
            repo = TaskRepository(db)
            for i in range(10):
                repo.create(
                    task_id=f"task-{i}",
                    url="https://example.com",
                    user_prompt=f"Task {i}",
                    owner_id=user.id
                )
            
            # List with limit
            tasks = repo.list_for_owner(user.id, limit=5)
            
            assert len(tasks) == 5
        finally:
            db.close()

    def test_list_for_owner_orders_by_created_at_desc(self, client):
        """Test list_for_owner returns tasks in descending order by created_at."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create user
            user_repo = UserRepository(db)
            user = user_repo.create(username="orderuser", password_hash="hash", email="order@example.com")
            
            # Create tasks
            repo = TaskRepository(db)
            task1 = repo.create(task_id="task1", url="https://example.com", user_prompt="T1", owner_id=user.id)
            task2 = repo.create(task_id="task2", url="https://example.com", user_prompt="T2", owner_id=user.id)
            task3 = repo.create(task_id="task3", url="https://example.com", user_prompt="T3", owner_id=user.id)
            
            # List tasks
            tasks = repo.list_for_owner(user.id)
            
            # Should be in reverse order (most recent first)
            assert tasks[0].task_id == "task3"
            assert tasks[1].task_id == "task2"
            assert tasks[2].task_id == "task1"
        finally:
            db.close()


class TestScheduleRepository:
    """Unit tests for ScheduleRepository."""

    def test_create_schedule_success(self, client):
        """Test creating a scheduled job."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create user
            user_repo = UserRepository(db)
            user = user_repo.create(username="scheduser", password_hash="hash", email="sched@example.com")
            
            repo = ScheduleRepository(db)
            job = repo.create(
                url="https://example.com",
                prompt="Daily scrape",
                cron="0 0 * * *",
                owner_id=user.id
            )
            
            assert job.id is not None
            assert job.url == "https://example.com"
            assert job.prompt == "Daily scrape"
            assert job.schedule_cron == "0 0 * * *"
            assert job.owner_id == user.id
            assert job.is_active is True
        finally:
            db.close()

    def test_list_for_owner_returns_user_jobs(self, client):
        """Test listing scheduled jobs for specific owner."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create users
            user_repo = UserRepository(db)
            user1 = user_repo.create(username="sched1", password_hash="hash1", email="s1@example.com")
            user2 = user_repo.create(username="sched2", password_hash="hash2", email="s2@example.com")
            
            # Create jobs
            repo = ScheduleRepository(db)
            repo.create(url="https://example.com", prompt="Job 1", cron="0 * * * *", owner_id=user1.id)
            repo.create(url="https://example.com", prompt="Job 2", cron="0 * * * *", owner_id=user1.id)
            repo.create(url="https://example.com", prompt="Job 3", cron="0 * * * *", owner_id=user2.id)
            
            # List jobs for user1
            jobs = repo.list_for_owner(user1.id)
            
            assert len(jobs) == 2
            assert all(j.owner_id == user1.id for j in jobs)
        finally:
            db.close()

    def test_delete_for_owner_success(self, client):
        """Test deleting job for owner."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create user and job
            user_repo = UserRepository(db)
            user = user_repo.create(username="deluser", password_hash="hash", email="del@example.com")
            
            repo = ScheduleRepository(db)
            job = repo.create(url="https://example.com", prompt="Delete me", cron="0 * * * *", owner_id=user.id)
            
            # Delete job
            result = repo.delete_for_owner(job.id, user.id)
            
            assert result is True
            
            # Verify deleted
            jobs = repo.list_for_owner(user.id)
            assert len(jobs) == 0
        finally:
            db.close()

    def test_delete_for_owner_wrong_owner_fails(self, client):
        """Test deleting job with wrong owner_id fails."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create users
            user_repo = UserRepository(db)
            user1 = user_repo.create(username="owner1", password_hash="hash1", email="o1@example.com")
            user2 = user_repo.create(username="owner2", password_hash="hash2", email="o2@example.com")
            
            # Create job for user1
            repo = ScheduleRepository(db)
            job = repo.create(url="https://example.com", prompt="Protected", cron="0 * * * *", owner_id=user1.id)
            
            # Try to delete as user2
            result = repo.delete_for_owner(job.id, user2.id)
            
            assert result is False
            
            # Verify job still exists
            jobs = repo.list_for_owner(user1.id)
            assert len(jobs) == 1
        finally:
            db.close()

    def test_delete_for_owner_nonexistent_job(self, client):
        """Test deleting non-existent job returns False."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create user
            user_repo = UserRepository(db)
            user = user_repo.create(username="nodeluser", password_hash="hash", email="nodel@example.com")
            
            repo = ScheduleRepository(db)
            result = repo.delete_for_owner(99999, user.id)
            
            assert result is False
        finally:
            db.close()


class TestParserRepository:
    """Unit tests for ParserRepository."""

    def test_find_cached_parser_by_domain(self, client):
        """Test finding cached parser by domain."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create domain
            domain = Domain(name="example.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            # Create parser
            parser = ParserCache(
                url_pattern="https://example.com/items",
                domain_id=domain.id,
                user_intent="Extract items",
                generated_regex=r"<div>(.*?)</div>",
                source_type="HTML",
                test_matches_count=5,
                confidence_score=85,
                created_by_task_id="test-task"
            )
            db.add(parser)
            db.commit()
            
            # Find parser
            repo = ParserRepository(db)
            parsers = repo.find_cached_parser(
                domain="example.com",
                confidence_threshold=70
            )
            
            assert len(parsers) > 0
            assert parsers[0].url_pattern == "https://example.com/items"
        finally:
            db.close()

    def test_find_cached_parser_filters_by_confidence(self, client):
        """Test finding parser filters by confidence threshold."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create domain
            domain = Domain(name="test.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            # Create parsers with different confidence scores
            parser1 = ParserCache(
                url_pattern="https://test.com/page1",
                domain_id=domain.id,
                user_intent="Extract",
                generated_regex=r"pattern1",
                source_type="HTML",
                test_matches_count=5,
                confidence_score=90,
                created_by_task_id="task1"
            )
            parser2 = ParserCache(
                url_pattern="https://test.com/page2",
                domain_id=domain.id,
                user_intent="Extract",
                generated_regex=r"pattern2",
                source_type="HTML",
                test_matches_count=3,
                confidence_score=60,
                created_by_task_id="task2"
            )
            db.add_all([parser1, parser2])
            db.commit()
            
            # Find with high threshold
            repo = ParserRepository(db)
            parsers = repo.find_cached_parser(
                domain="test.com",
                confidence_threshold=80
            )
            
            assert len(parsers) == 1
            assert parsers[0].confidence_score == 90
        finally:
            db.close()

    def test_find_cached_parser_filters_by_active(self, client):
        """Test finding parser filters by is_active flag."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create domain
            domain = Domain(name="active.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            # Create active and inactive parsers
            parser1 = ParserCache(
                url_pattern="https://active.com/page1",
                domain_id=domain.id,
                user_intent="Extract",
                generated_regex=r"pattern1",
                source_type="HTML",
                test_matches_count=5,
                confidence_score=85,
                is_active=True,
                created_by_task_id="task1"
            )
            parser2 = ParserCache(
                url_pattern="https://active.com/page2",
                domain_id=domain.id,
                user_intent="Extract",
                generated_regex=r"pattern2",
                source_type="HTML",
                test_matches_count=3,
                confidence_score=85,
                is_active=False,
                created_by_task_id="task2"
            )
            db.add_all([parser1, parser2])
            db.commit()
            
            # Find parsers
            repo = ParserRepository(db)
            parsers = repo.find_cached_parser(domain="active.com")
            
            # Should only return active parser
            assert len(parsers) == 1
            assert parsers[0].is_active is True
        finally:
            db.close()

    def test_find_cached_parser_orders_by_confidence_and_last_used(self, client):
        """Test finding parser orders by confidence and last_used_at."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create domain
            domain = Domain(name="order.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            # Create parsers with same confidence
            parser1 = ParserCache(
                url_pattern="https://order.com/p1",
                domain_id=domain.id,
                user_intent="Extract",
                generated_regex=r"p1",
                source_type="HTML",
                test_matches_count=5,
                confidence_score=85,
                last_used_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                created_by_task_id="t1"
            )
            parser2 = ParserCache(
                url_pattern="https://order.com/p2",
                domain_id=domain.id,
                user_intent="Extract",
                generated_regex=r"p2",
                source_type="HTML",
                test_matches_count=5,
                confidence_score=85,
                last_used_at=datetime(2024, 12, 1, tzinfo=timezone.utc),
                created_by_task_id="t2"
            )
            db.add_all([parser1, parser2])
            db.commit()
            
            # Find parsers
            repo = ParserRepository(db)
            parsers = repo.find_cached_parser(domain="order.com")
            
            # Should return most recently used first
            assert parsers[0].url_pattern == "https://order.com/p2"
        finally:
            db.close()

    def test_find_cached_parser_with_keyword_matching(self, client):
        """Test finding parser with keyword overlap scoring."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create domain
            domain = Domain(name="keywords.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            # Create parser with keywords
            parser = ParserCache(
                url_pattern="https://keywords.com/page",
                domain_id=domain.id,
                user_intent="Extract jobs",
                keyword_set=["python", "developer", "remote"],
                generated_regex=r"pattern",
                source_type="HTML",
                test_matches_count=5,
                confidence_score=85,
                created_by_task_id="task"
            )
            db.add(parser)
            db.commit()
            
            # Find with matching keywords
            repo = ParserRepository(db)
            parsers = repo.find_cached_parser(
                domain="keywords.com",
                keywords=["python", "remote"]
            )
            
            assert len(parsers) > 0
        finally:
            db.close()

    def test_find_cached_parser_respects_limit(self, client):
        """Test finding parser respects limit parameter."""
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            # Create domain
            domain = Domain(name="limit.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            # Create multiple parsers
            for i in range(10):
                parser = ParserCache(
                    url_pattern=f"https://limit.com/page{i}",
                    domain_id=domain.id,
                    user_intent="Extract",
                    generated_regex=f"pattern{i}",
                    source_type="HTML",
                    test_matches_count=5,
                    confidence_score=85,
                    created_by_task_id=f"task{i}"
                )
                db.add(parser)
            db.commit()
            
            # Find with limit
            repo = ParserRepository(db)
            parsers = repo.find_cached_parser(domain="limit.com", limit=5)
            
            assert len(parsers) == 5
        finally:
            db.close()
