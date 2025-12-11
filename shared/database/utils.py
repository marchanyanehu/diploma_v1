"""
Simple database utilities for basic CRUD operations.

This module provides basic database operations without complex
business logic to avoid SQLAlchemy typing issues.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict, Any, Iterable
from datetime import datetime, timezone
import hashlib
import logging

from .models import (
    ScrapingTask, ParserCache, User, ScheduledJob,
    Domain, TaskSourceData, TaskIntent, ParserSample
)

logger = logging.getLogger(__name__)


def get_or_create_domain(db: Session, domain_name: str) -> Domain:
    """Get existing domain or create a new one."""
    domain = db.query(Domain).filter(Domain.name == domain_name).first()
    if not domain:
        domain = Domain(name=domain_name)
        db.add(domain)
        db.flush()  # Get the ID without committing
    return domain


def create_user(db: Session, username: str, password_hash: str, email: Optional[str] = None) -> User:
    """Create a new user."""
    user = User(username=username, hashed_password=password_hash, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()

def create_scraping_task(
    db: Session,
    task_id: str,
    url: str,
    user_prompt: str,
    status: str = "PENDING",
    owner_id: Optional[int] = None
) -> ScrapingTask:
    """Create a new scraping task."""
    task = ScrapingTask(
        task_id=task_id,
        url=url,
        user_prompt=user_prompt,
        status=status,
        owner_id=owner_id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info(f"Created scraping task: {task_id}")
    return task


def get_scraping_task(db: Session, task_id: str) -> Optional[ScrapingTask]:
    """Get a scraping task by task_id."""
    return db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).first()


def update_task_status(
    db: Session,
    task_id: str,
    status: str,
    error_message: Optional[str] = None
) -> Optional[ScrapingTask]:
    """Update the status of a scraping task."""
    task = get_scraping_task(db, task_id)
    if task:
        # Normalize STARTED to IN_PROGRESS to align with API enums
        normalized_status = "IN_PROGRESS" if status.upper() == "STARTED" else status

        update_data: Dict[Any, Any] = {
            ScrapingTask.status: normalized_status,
            ScrapingTask.error_message: error_message
        }

        now = datetime.now(timezone.utc)
        # Populate lifecycle timestamps to keep progress reporting meaningful
        if normalized_status == "IN_PROGRESS" and task.started_at is None:
            update_data[ScrapingTask.started_at] = now
        if normalized_status in ("SUCCESS", "FAILED"):
            update_data[ScrapingTask.completed_at] = now

        # Use UPDATE query to avoid SQLAlchemy attribute assignment issues
        db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).update(update_data)
        db.commit()
        # Refresh to get updated data
        db.refresh(task)
    return task


def update_task_sources(
    db: Session,
    task_id: str,
    *,
    page_content: Optional[str] = None,
    html_content: Optional[str] = None,
    network_requests: Optional[List[Dict[str, Any]]] = None,
    intent: Optional[Dict[str, Any]] = None,
    started_at: Optional[datetime] = None,
) -> None:
    """Persist raw capture artifacts early in the pipeline.

    This allows later debugging / iterative improvement even if regex generation
    fails. Truncates large blobs defensively.
    
    Uses normalized tables: TaskSourceData for page/network data, TaskIntent for intent data.
    """
    task = get_scraping_task(db, task_id)
    if not task:  # silently ignore if missing
        return
    MAX_PAGE_LEN = 500_000  # ~500 KB safeguard
    MAX_NETWORK_EVENTS = 100
    MAX_BODY_PREVIEW_LEN = 50_000
    
    # Update started_at on the main task if provided
    if started_at is not None:
        db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).update({
            ScrapingTask.started_at: started_at
        })
    
    # Store page content, html content, and network requests in TaskSourceData table
    if page_content is not None or html_content is not None or network_requests is not None:
        safe_page = None
        if page_content is not None:
            safe_page = page_content[:MAX_PAGE_LEN]
        
        safe_html = None
        if html_content is not None:
            safe_html = html_content[:MAX_PAGE_LEN]
        
        safe_network: List[Dict[str, Any]] | None = None
        if network_requests is not None:
            trimmed: List[Dict[str, Any]] = []
            for ev in network_requests[:MAX_NETWORK_EVENTS]:
                ev_copy = dict(ev)
                body_prev = ev_copy.get("body_preview")
                if isinstance(body_prev, str) and len(body_prev) > MAX_BODY_PREVIEW_LEN:
                    ev_copy["body_preview"] = body_prev[:MAX_BODY_PREVIEW_LEN]
                    ev_copy["body_truncated"] = True
                trimmed.append(ev_copy)
            safe_network = trimmed
        
        # Check if TaskSourceData already exists for this task
        existing_source = db.query(TaskSourceData).filter(TaskSourceData.task_id == task.id).first()
        if existing_source:
            # Update existing record
            update_data: Dict[Any, Any] = {}
            if safe_page is not None:
                update_data[TaskSourceData.page_content] = safe_page
            if safe_html is not None:
                update_data[TaskSourceData.html_content] = safe_html
            if safe_network is not None:
                update_data[TaskSourceData.network_requests] = safe_network
            if update_data:
                db.query(TaskSourceData).filter(TaskSourceData.task_id == task.id).update(update_data)
        else:
            # Create new TaskSourceData record
            task_source = TaskSourceData(
                task_id=task.id,
                page_content=safe_page,
                html_content=safe_html,
                network_requests=safe_network
            )
            db.add(task_source)
    
    # Store intent data in TaskIntent table
    if intent:
        # Create normalized hash for intent matching
        intent_parts = [intent.get("target", ""), *(intent.get("keywords") or [])]
        normalized_hash = hashlib.sha1("|".join(sorted(p for p in intent_parts if p)).encode("utf-8")).hexdigest()
        
        # Create new TaskIntent record with all fields
        task_intent = TaskIntent(
            target=intent.get("target"),
            keywords=intent.get("keywords"),
            schema_fields=intent.get("schema_fields"),
            constraints=intent.get("constraints"),
            output_shape=intent.get("output_shape"),
            confidence=intent.get("confidence"),
            normalized_hash=normalized_hash,
            source_type=intent.get("source_type"),
            target_attribute=intent.get("target_attribute")
        )
        db.add(task_intent)
        db.flush()  # Get the ID
        
        # Link task to the intent
        db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).update({
            ScrapingTask.intent_id: task_intent.id
        })
    
    db.commit()


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


def create_scheduled_job(
    db: Session,
    url: str,
    prompt: str,
    cron: str,
    owner_id: int
) -> ScheduledJob:
    job = ScheduledJob(url=url, prompt=prompt, schedule_cron=cron, owner_id=owner_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def get_scheduled_jobs_by_user(db: Session, owner_id: int) -> List[ScheduledJob]:
    return db.query(ScheduledJob).filter(ScheduledJob.owner_id == owner_id).all()

def get_due_jobs(db: Session) -> List[ScheduledJob]:
    """Get all active scheduled jobs that are due to run."""
    now = datetime.now(timezone.utc)
    return db.query(ScheduledJob).filter(
        ScheduledJob.is_active == True,
        ScheduledJob.next_run_at <= now
    ).all()

def delete_scheduled_job(db: Session, job_id: int, owner_id: int) -> bool:
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id, ScheduledJob.owner_id == owner_id).first()
    if job:
        db.delete(job)
        db.commit()
        return True
    return False


def update_parser_usage(db: Session, parser_id: int, success: bool = True) -> None:
    """Update usage statistics for a parser when it's used.
    
    Increments times_used, updates last_used_at, and adjusts confidence_score based on success.
    """
    parser = db.query(ParserCache).filter(ParserCache.id == parser_id).first()
    if not parser:
        return
    
    update_data: Dict[Any, Any] = {
        ParserCache.times_used: ParserCache.times_used + 1,
        ParserCache.last_used_at: datetime.now(timezone.utc),
    }
    
    # Adjust success rate based on outcome
    if success:
        # Slightly increase confidence on success (max 100)
        new_confidence = min(100, parser.confidence_score + 1)
        new_success_rate = min(100, parser.success_rate + 1)
    else:
        # Decrease confidence on failure
        new_confidence = max(0, parser.confidence_score - 5)
        new_success_rate = max(0, parser.success_rate - 10)
    
    update_data[ParserCache.confidence_score] = new_confidence
    update_data[ParserCache.success_rate] = new_success_rate
    
    db.query(ParserCache).filter(ParserCache.id == parser_id).update(update_data)
    db.commit()


def find_cached_parser_by_fields(
    db: Session,
    domain: str,
    fields: List[str],
    source_type: str = "SEMANTIC",
    confidence_threshold: int = 70,
    limit: int = 3,
    url_pattern: Optional[str] = None,
) -> List[ParserCache]:
    """Find cached parsers by domain + complete URL + field combination.
    
    This allows regex reuse across different prompts as long as they extract
    the same fields from the exact same URL.
    
    Args:
        db: Database session
        domain: Domain name (e.g., 'puko.lt')
        fields: List of field names (e.g., ['title', 'price'])
        source_type: Content type ('SEMANTIC', 'HTML', 'JSON')
        confidence_threshold: Minimum confidence score
        limit: Max parsers to return
        url_pattern: Complete URL for precise matching
        
    Returns:
        List of matching ParserCache objects, ordered by best match
    """
    # Normalize fields to lowercase sorted set for matching
    field_set = sorted([f.lower() for f in fields])
    
    # Query parsers for this domain and source type
    filters = [
        Domain.name == domain,
        ParserCache.source_type == source_type,
        ParserCache.confidence_score >= confidence_threshold,
        ParserCache.is_active == True,  # noqa: E712
    ]
    
    # Add URL matching if provided (exact match)
    if url_pattern:
        filters.append(ParserCache.url_pattern == url_pattern)
    
    q = (
        db.query(ParserCache)
        .join(Domain, ParserCache.domain_id == Domain.id)
        .filter(*filters)
        .order_by(ParserCache.confidence_score.desc(), ParserCache.last_used_at.desc().nullslast())
    )
    
    parsers = list(q.limit(20))  # Get more candidates to filter by fields
    
    # Filter by field match
    scored: List[tuple[int, int, ParserCache]] = []
    for p in parsers:
        # keyword_set stores the field names for field-based caching
        p_fields = sorted([f.lower() for f in (p.keyword_set or [])])
        
        # Exact match preferred
        if p_fields == field_set:
            scored.append((100, p.confidence_score, p))
        # Superset match (parser extracts more fields than needed)
        elif set(field_set).issubset(set(p_fields)):
            overlap = len(set(field_set) & set(p_fields))
            scored.append((overlap * 10, p.confidence_score, p))
    
    # Sort by match quality, then confidence
    scored.sort(key=lambda t: (-t[0], -t[1]))
    return [p for _, _, p in scored[:limit]]


def create_parser_cache_by_fields(
    db: Session,
    domain: str,
    fields: List[str],
    generated_regex: str,
    source_type: str,
    created_by_task_id: str,
    test_matches_count: int,
    confidence_score: int = 90,
    url_pattern: Optional[str] = None,
    sample_input: Optional[str] = None,
    sample_output: Optional[List[Dict[str, Any]]] = None
) -> ParserCache:
    """Create parser cache entry indexed by fields and complete URL.
    
    This allows the same regex to be reused for different prompts
    as long as they extract the same fields from the exact same URL.
    
    Args:
        db: Database session
        domain: Domain name
        fields: List of field names being extracted
        generated_regex: The regex pattern
        source_type: Content type ('SEMANTIC', 'HTML', 'JSON')
        created_by_task_id: Task that created this parser
        test_matches_count: Number of items matched during generation
        confidence_score: Initial confidence (0-100)
        url_pattern: Complete URL for precise caching
        sample_input: Sample input content used for regex generation
        sample_output: Sample extracted items
        
    Returns:
        Created ParserCache object
    """
    # Get or create domain
    domain_record = get_or_create_domain(db, domain)
    
    # Store fields in keyword_set for matching
    field_set = sorted([f.lower() for f in fields])
    
    # Create intent keywords from fields for compatibility
    intent_keywords = field_set.copy()
    
    # Use provided url_pattern (full URL) or fall back to domain-only
    final_url_pattern = url_pattern if url_pattern else f"{domain}/*"
    
    parser = ParserCache(
        url_pattern=final_url_pattern,  # Full URL for precise matching
        domain_id=domain_record.id,
        user_intent=f"Extract: {', '.join(fields)}",
        intent_keywords=intent_keywords,
        keyword_set=field_set,  # Field names for indexing
        generated_regex=generated_regex,
        source_type=source_type,
        source_identifier=f"{source_type.lower()}_content",
        created_by_task_id=created_by_task_id,
        test_matches_count=test_matches_count,
        confidence_score=confidence_score,
        success_rate=100,
        is_active=True,
        times_used=0
    )
    db.add(parser)
    db.flush()  # Get the parser ID
    
    # Create sample record if sample data provided
    if sample_input or sample_output:
        sample = ParserSample(
            parser_id=parser.id,
            sample_input=(sample_input or "")[:5000],
            sample_output=sample_output[:10] if sample_output else None
        )
        db.add(sample)
    
    db.commit()
    db.refresh(parser)
    logger.info(f"Created field-based parser cache for {final_url_pattern}: {fields} (id={parser.id})")
    return parser


def invalidate_parser(db: Session, parser_id: int) -> None:
    """Invalidate a parser that failed validation.
    
    Marks parser as inactive so it won't be used again.
    Can be removed entirely or kept for analytics.
    """
    db.query(ParserCache).filter(ParserCache.id == parser_id).update({
        ParserCache.is_active: False,
        ParserCache.confidence_score: 0
    })
    db.commit()
    logger.info(f"Invalidated parser {parser_id}")
