"""
Simple database utilities for basic CRUD operations.

This module provides basic database operations without complex
business logic to avoid SQLAlchemy typing issues.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict, Any, Iterable
from datetime import datetime, timezone
import logging

from .db_models import ScrapingTask, ParserCache

logger = logging.getLogger(__name__)


def create_scraping_task(
    db: Session,
    task_id: str,
    url: str,
    user_prompt: str,
    status: str = "PENDING"
) -> ScrapingTask:
    """Create a new scraping task."""
    task = ScrapingTask(
        task_id=task_id,
        url=url,
        user_prompt=user_prompt,
        status=status
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info(f"Created scraping task: {task_id}")
    return task


def get_scraping_task(db: Session, task_id: str) -> Optional[ScrapingTask]:
    """Get a scraping task by task_id."""
    return db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).first()


def create_parser_cache(
    db: Session,
    url_pattern: str,
    domain: str,
    user_intent: str,
    generated_regex: str,
    source_type: str,
    created_by_task_id: str,
    test_matches_count: int
) -> ParserCache:
    """Create a new parser cache entry."""
    parser = ParserCache(
        url_pattern=url_pattern,
        domain=domain,
        user_intent=user_intent,
        generated_regex=generated_regex,
        source_type=source_type,
        created_by_task_id=created_by_task_id,
        test_matches_count=test_matches_count
    )
    db.add(parser)
    db.commit()
    db.refresh(parser)
    logger.info(f"Created parser cache for domain: {domain}")
    return parser


def find_cached_parser(
    db: Session,
    domain: str,
    keywords: Iterable[str] | None = None,
    confidence_threshold: int = 70,
    limit: int = 3,
) -> List[ParserCache]:
    """Find candidate cached parsers for a domain filtered by keyword overlap.

    Returns multiple candidates (ordered best-first) so caller can choose.
    """
    q = (
        db.query(ParserCache)
        .filter(
            ParserCache.domain == domain,
            ParserCache.confidence_score >= confidence_threshold,
        )
        .order_by(ParserCache.confidence_score.desc(), ParserCache.last_used_at.desc().nullslast())
    )
    parsers = list(q.limit(limit))
    if keywords:
        kw_low = {k.lower() for k in keywords if k}
        scored: List[tuple[int, ParserCache]] = []
        for p in parsers:
            p_kws = {k.lower() for k in (p.intent_keywords or [])}
            overlap = len(kw_low & p_kws)
            scored.append((overlap, p))
        scored.sort(key=lambda t: (-t[0], -t[1].confidence_score))
        return [p for _, p in scored if _ > 0] or parsers
    return parsers


def update_task_status(
    db: Session,
    task_id: str,
    status: str,
    error_message: Optional[str] = None
) -> Optional[ScrapingTask]:
    """Update the status of a scraping task."""
    task = get_scraping_task(db, task_id)
    if task:
        # Use UPDATE query to avoid SQLAlchemy attribute assignment issues
        db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).update({
            ScrapingTask.status: status,
            ScrapingTask.error_message: error_message
        })
        db.commit()
        # Refresh to get updated data
        db.refresh(task)
    return task


def persist_extraction_result(
    db: Session,
    task_id: str,
    *,
    extracted_data: List[Dict[str, Any]],
    total_matches: int,
    used_parser: Optional[ParserCache] = None,
    processing_time_seconds: Optional[int] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    used_cached_parser: bool = False,
):
    """Persist final extraction result onto a task row."""
    from .db_models import ScrapingTask  # local import to avoid circular issues

    update_data: Dict[Any, Any] = {
        ScrapingTask.extracted_data: extracted_data,
        ScrapingTask.total_matches: total_matches,
        ScrapingTask.status: "SUCCESS",
        ScrapingTask.used_cached_parser: used_cached_parser,
        ScrapingTask.processing_time_seconds: processing_time_seconds,
    }
    if used_parser:
        update_data[ScrapingTask.used_parser_id] = used_parser.id
        update_data[ScrapingTask.used_cached_parser] = used_cached_parser
    if started_at:
        update_data[ScrapingTask.started_at] = started_at
    if completed_at:
        update_data[ScrapingTask.completed_at] = completed_at

    db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).update(update_data)
    db.commit()


def record_new_parser(
    db: Session,
    *,
    task_id: str,
    url: str,
    intent: Dict[str, Any],
    pattern: str,
    flags: str,
    matches_count: int,
    source_type: str,
    sample_input: str | None,
    sample_output: List[Dict[str, Any]] | None,
) -> Optional[ParserCache]:
    """Create a new ParserCache entry if pattern seems valid."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        # Compose final stored regex (embed flags inline if provided)
        if flags:
            stored_regex = f"(?{flags}:{pattern})"
        else:
            stored_regex = pattern
        parser = ParserCache(
            url_pattern=url,
            domain=domain,
            user_intent=intent.get("target", intent.get("original_input", ""))[:255],
            intent_keywords=intent.get("keywords", [])[:25],
            target_data_type=intent.get("target", "")[:100],
            generated_regex=stored_regex,
            source_type=source_type,
            source_identifier=url,
            test_matches_count=matches_count,
            created_by_task_id=task_id,
            sample_input=(sample_input or "")[:5000],
            sample_output=sample_output[:10] if sample_output else None,
            confidence_score=100,
            success_rate=100,
        )
        db.add(parser)
        db.commit()
        db.refresh(parser)
        return parser
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to create parser cache: %s", e)
        db.rollback()
        return None


def get_all_tasks(db: Session, limit: int = 10) -> List[ScrapingTask]:
    """Get recent scraping tasks."""
    return (
        db.query(ScrapingTask)
        .order_by(ScrapingTask.created_at.desc())
        .limit(limit)
        .all()
    )
