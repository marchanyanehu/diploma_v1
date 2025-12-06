"""
Helpers for translating ORM task entities into API response models.

Keeps presentation logic separate from transport (FastAPI) and persistence layers.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

from ..db_models import ScrapingTask
from ..models import TaskStatus, TaskStatusResponse, ScrapeResult


def normalize_status(task: ScrapingTask) -> TaskStatus:
    """Map raw DB status string to TaskStatus enum with safe fallback."""
    try:
        return TaskStatus(cast(str, getattr(task, "status", "")))
    except ValueError:
        return TaskStatus.FAILED


def extract_timestamps(task: ScrapingTask) -> tuple[datetime, datetime]:
    """Derive created/updated timestamps with sensible defaults."""
    created_at: datetime = cast(
        datetime, getattr(task, "created_at", None) or datetime.now(timezone.utc)
    )
    updated_at: datetime = cast(
        datetime,
        getattr(task, "completed_at", None)
        or getattr(task, "started_at", None)
        or created_at,
    )
    return created_at, updated_at


def build_status_response(task: ScrapingTask) -> TaskStatusResponse:
    """Construct TaskStatusResponse from ORM task."""
    status_enum = normalize_status(task)
    created_at, updated_at = extract_timestamps(task)
    err_msg: Optional[str] = cast(Optional[str], getattr(task, "error_message", None))
    return TaskStatusResponse(
        task_id=cast(str, getattr(task, "task_id", "")),
        status=status_enum,
        progress=None,
        message=err_msg,
        created_at=created_at,
        updated_at=updated_at,
    )


def build_result_response(task: ScrapingTask) -> ScrapeResult:
    """Construct ScrapeResult for SUCCESS state."""
    status_enum = normalize_status(task)
    created_at, _ = extract_timestamps(task)
    completed_at: Optional[datetime] = cast(Optional[datetime], getattr(task, "completed_at", None))
    processing_seconds: Optional[int] = cast(Optional[int], getattr(task, "processing_time_seconds", None))
    used_cached: bool = bool(getattr(task, "used_cached_parser", False))
    total_matches: Optional[int] = cast(Optional[int], getattr(task, "total_matches", None))
    parser_id: Optional[int] = cast(Optional[int], getattr(task, "used_parser_id", None))

    metadata: Dict[str, Any] = {
        "total_matches": total_matches,
        "used_cached_parser": used_cached,
        "used_parser_id": parser_id,
    }

    return ScrapeResult(
        task_id=cast(str, getattr(task, "task_id", "")),
        status=status_enum,
        url=cast(str, getattr(task, "url", "")),
        prompt=cast(str, getattr(task, "user_prompt", "")),
        data=getattr(task, "extracted_data", None) or [],
        metadata={k: v for k, v in metadata.items() if v is not None},
        processing_time=float(processing_seconds) if processing_seconds is not None else None,
        created_at=created_at,
        completed_at=completed_at,
    )

