"""
Task orchestration services to enforce SOLID responsibilities.

This module encapsulates task creation, authorization checks, and queue
dispatching so FastAPI routes remain thin and focused on transport concerns.
"""

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4
import logging

from sqlalchemy.orm import Session

from ..schemas import TaskStatus
from ..repositories import TaskRepository

logger = logging.getLogger(__name__)


class TaskQueue(Protocol):
    """Minimal queue abstraction to keep TaskService decoupled from Celery."""

    def enqueue(self, task_name: str, args: list[Any], correlation_id: str | None = None) -> None:  # pragma: no cover - protocol
        ...


class CeleryTaskQueue:
    """Concrete queue backed by Celery send_task."""

    def __init__(self, celery_app: Any, queue_name: str = "ai_queue") -> None:
        self.celery_app = celery_app
        self.queue_name = queue_name

    def enqueue(self, task_name: str, args: list[Any], correlation_id: str | None = None) -> None:
        headers = {"correlation_id": correlation_id} if correlation_id else None
        self.celery_app.send_task(task_name, args=args, queue=self.queue_name, headers=headers)


class TaskNotFoundError(Exception):
    """Raised when a task does not exist."""


class TaskForbiddenError(Exception):
    """Raised when a user tries to access a task they do not own."""


@dataclass
class TaskService:
    """Business logic for scraping tasks (SRP, DIP-friendly)."""

    db: Session
    queue: TaskQueue
    task_repo: TaskRepository

    def create_task(self, url: str, prompt: str, owner_id: int, correlation_id: str | None = None) -> str:
        """Create a task record and enqueue async processing."""
        task_id = str(uuid4())
        try:
            self.task_repo.create(
                task_id=task_id,
                url=url,
                user_prompt=prompt,
                status=TaskStatus.PENDING,
                owner_id=owner_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("task_service.create_task.persist_failed", extra={"task_id": task_id, "error": str(exc)})

        # Queue async work
        try:
            self.queue.enqueue(
                "scrape.process_request_full",
                [task_id, url, prompt],
                correlation_id=correlation_id,
            )
            logger.info("task_service.create_task.enqueued", extra={"task_id": task_id})
        except Exception as exc:  # noqa: BLE001
            logger.error("task_service.create_task.enqueue_failed", extra={"task_id": task_id, "error": str(exc)})

        return task_id

    def get_task_for_user(self, task_id: str, owner_id: int):
        """Fetch a task and ensure ownership constraints."""
        task = self.task_repo.get_by_task_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        if task.owner_id != owner_id:
            raise TaskForbiddenError(task_id)
        return task

