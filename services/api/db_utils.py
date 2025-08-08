"""
Simple database utilities for basic CRUD operations.

This module provides basic database operations without complex
business logic to avoid SQLAlchemy typing issues.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
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
    confidence_threshold: int = 70
) -> Optional[ParserCache]:
    """Find a cached parser for a domain."""
    return (
        db.query(ParserCache)
        .filter(
            ParserCache.domain == domain,
            ParserCache.confidence_score >= confidence_threshold
        )
        .order_by(ParserCache.confidence_score.desc())
        .first()
    )


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


def get_all_tasks(db: Session, limit: int = 10) -> List[ScrapingTask]:
    """Get recent scraping tasks."""
    return (
        db.query(ScrapingTask)
        .order_by(ScrapingTask.created_at.desc())
        .limit(limit)
        .all()
    )
