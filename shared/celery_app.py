"""
Shared Celery application factory and instance.

This module centralizes Celery configuration so both the API and the
worker import the same app. It reads configuration from environment
variables with sensible defaults.
"""

from __future__ import annotations

import os
from celery import Celery
import logging

logger = logging.getLogger(__name__)


def _get_broker_backend() -> tuple[str, str]:
    """Resolve broker and backend URLs from environment variables.

    Priority:
    - CELERY_BROKER_URL / CELERY_RESULT_BACKEND
    - REDIS_URL (used for both broker and backend)
    - Fallback to redis://localhost:6379/0
    """
    default = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    broker = os.getenv("CELERY_BROKER_URL", default)
    backend = os.getenv("CELERY_RESULT_BACKEND", default)
    return broker, backend


def _make_celery() -> Celery:
    broker, backend = _get_broker_backend()
    app = Celery(
        "aggregator",
        broker=broker,
        backend=backend,
        include=[
            # Ensure tasks module is auto-registered when worker starts
            "services.headless_worker.tasks",
            "services.ai_worker.tasks",
            "services.scheduler.tasks",
        ],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=60 * 15,  # 15 minutes hard limit
        task_soft_time_limit=60 * 10,  # 10 minutes soft limit
        task_publish_retry=True,
        task_publish_retry_policy={
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.5,
            "interval_max": 2,
        },
        task_routes={
            "services.headless_worker.tasks.*": {"queue": "fetching_queue"},
            "services.ai_worker.tasks.*": {"queue": "ai_queue"},
            "services.scheduler.tasks.*": {"queue": "ai_queue"},
            "scrape.fetch_url": {"queue": "fetching_queue"},
            "scrape.fetch_page": {"queue": "fetching_queue"},
            "scrape.process_request_full": {"queue": "ai_queue"},
            "scrape.process_content": {"queue": "ai_queue"},
            "scheduler.check_due_jobs": {"queue": "ai_queue"},
        },
        beat_schedule={
            "check-every-minute": {
                "task": "scheduler.check_due_jobs",
                "schedule": 60.0,
            },
        },
    )
    # Optional eager (synchronous) mode for local dev / tests without broker
    if os.getenv("CELERY_EAGER") or os.getenv("CELERY_ALWAYS_EAGER"):
        app.conf.task_always_eager = True
        app.conf.task_eager_propagates = True
        logger.info("Celery running in EAGER (synchronous) mode – tasks execute inline.")
    return app


# Global Celery instance to be imported by API and worker
celery_app: Celery = _make_celery()
