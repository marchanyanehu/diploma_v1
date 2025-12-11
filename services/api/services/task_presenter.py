"""
Helpers for translating ORM task entities into API response models.

Keeps presentation logic separate from transport (FastAPI) and persistence layers.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

from shared.database import ScrapingTask
from ..schemas import TaskStatus, TaskStatusResponse, ScrapeResult


def normalize_status(task: ScrapingTask) -> TaskStatus:
    """Map raw DB status string to TaskStatus enum with safe fallback."""
    raw_status = (cast(str, getattr(task, "status", "") or "")).upper()
    # If data exists but status is failed, trust data (late-status write guard)
    has_data = bool(getattr(task, "extracted_data", None))
    if raw_status == "FAILED" and has_data:
        return TaskStatus.SUCCESS
    if raw_status == "STARTED":
        return TaskStatus.IN_PROGRESS
    if raw_status in ("PENDING", "IN_PROGRESS", "SUCCESS", "FAILED"):
        return cast(TaskStatus, raw_status)
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


def derive_progress(task: ScrapingTask, status_enum: TaskStatus) -> Optional[int]:
    """
    Provide a lightweight progress hint derived from timestamps/status.
    Keeps API responses informative even without a dedicated progress column.
    """
    if status_enum == TaskStatus.SUCCESS:
        return 100
    if status_enum == TaskStatus.FAILED:
        # Failed but finished running
        return 100 if getattr(task, "completed_at", None) else 0
    if status_enum == TaskStatus.IN_PROGRESS:
        return 50 if getattr(task, "started_at", None) else 10
    # Pending
    return 0


def derive_message(status_enum: TaskStatus, error_message: Optional[str]) -> Optional[str]:
    """Generate a user-friendly message when none is stored."""
    if error_message:
        return error_message
    if status_enum == TaskStatus.SUCCESS:
        return "Task completed successfully"
    if status_enum == TaskStatus.IN_PROGRESS:
        return "Task is in progress"
    if status_enum == TaskStatus.PENDING:
        return "Task is pending in the queue"
    if status_enum == TaskStatus.FAILED:
        return "Task failed"
    return None


def build_status_response(task: ScrapingTask) -> TaskStatusResponse:
    """Construct TaskStatusResponse from ORM task."""
    status_enum = normalize_status(task)
    created_at, updated_at = extract_timestamps(task)
    err_msg: Optional[str] = cast(Optional[str], getattr(task, "error_message", None))
    progress = derive_progress(task, status_enum)
    message = derive_message(status_enum, err_msg)
    return TaskStatusResponse(
        task_id=cast(str, getattr(task, "task_id", "")),
        status=status_enum,
        progress=progress,
        message=message,
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

