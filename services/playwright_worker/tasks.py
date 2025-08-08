"""
Celery tasks for the Playwright worker.

For Task #203 we create a minimal task that simulates the scraping
pipeline and updates the task status in the database. Next tasks will
replace the simulation with real Playwright + LLM logic.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict
from urllib.parse import urlparse

from pydantic import HttpUrl, TypeAdapter

from shared.celery_app import celery_app

# Import database utilities from API service layer.
# In a larger project you'd extract shared DB code into `shared/`.
from services.api.database import SessionLocal
from services.api import db_utils

logger = logging.getLogger(__name__)


@celery_app.task(name="scrape.process_request")
def process_request_task(task_id: str, url: str, prompt: str) -> Dict[str, Any]:
    """Background task entrypoint for processing a scraping request.

    For now, it simulates work with sleeps and updates DB status. It returns
    a simple result payload. Subsequent tasks will perform real scraping
    and LLM-driven extraction.
    """
    db = SessionLocal()
    try:
        # Mark as IN_PROGRESS
        db_utils.update_task_status(db, task_id=task_id, status="IN_PROGRESS")
        logger.info(f"Task {task_id} started for URL: {url}")

        # Simulate scraping work
        time.sleep(1)

        # Simulate a successful extraction result
        result = {
            "items": [
                {"text": "Example item 1", "source": "simulated", "confidence": 0.9},
                {"text": "Example item 2", "source": "simulated", "confidence": 0.85},
            ]
        }

        # Persist a minimal success footprint (optional for now)
        # Here we could update extracted_data/total_matches etc. For Task #203,
        # we just mark status SUCCESS.
        db_utils.update_task_status(db, task_id=task_id, status="SUCCESS")
        logger.info(f"Task {task_id} completed successfully")

        return {"task_id": task_id, "status": "SUCCESS", "result": result}
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Task {task_id} failed: {exc}")
        db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message=str(exc))
        raise
    finally:
        db.close()


@celery_app.task(name="scrape.fetch_url")
def fetch_url(url: str) -> Dict[str, Any]:
    """Minimal Celery task that accepts a URL and returns a normalized payload.

    This satisfies EPIC #3 Task #303. Later tasks (#304+) will use Playwright to
    actually navigate and collect data. Here we just validate/normalize the URL
    and return basic metadata so the pipeline can be wired end-to-end.

    Args:
        url: The target page URL provided by the client.

    Returns:
        A dict with the normalized URL and simple metadata.

    Raises:
        ValueError: If the provided URL is invalid.
    """
    logger.info("Received fetch_url task for: %s", url)

    # Validate and normalize URL via Pydantic v2 TypeAdapter
    adapter: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)
    try:
        valid = adapter.validate_python(url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Invalid URL provided to fetch_url: %s | error: %s", url, exc)
        raise ValueError(f"Invalid URL: {url}") from exc

    normalized_url = str(valid)
    parts = urlparse(normalized_url)
    host = parts.netloc

    payload: Dict[str, Any] = {
        "status": "RECEIVED",
        "url": normalized_url,
        "host": host,
    }
    logger.info("fetch_url normalized payload: %s", payload)
    return payload
