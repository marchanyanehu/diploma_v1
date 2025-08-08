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
