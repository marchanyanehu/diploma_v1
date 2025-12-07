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

from .db_models import (
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
    # Get or create the domain record
    domain_record = get_or_create_domain(db, domain)
    
    parser = ParserCache(
        url_pattern=url_pattern,
        domain_id=domain_record.id,
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
    # Join with domains table to filter by domain name
    q = (
        db.query(ParserCache)
        .join(Domain, ParserCache.domain_id == Domain.id)
        .filter(
            Domain.name == domain,
            ParserCache.confidence_score >= confidence_threshold,
            ParserCache.is_active == True,  # noqa: E712
        )
        .order_by(ParserCache.confidence_score.desc(), ParserCache.last_used_at.desc().nullslast())
    )
    parsers = list(q.limit(limit))
    if keywords:
        kw_low = {k.lower() for k in keywords if k}
        scored: List[tuple[int, int, ParserCache]] = []
        for p in parsers:
            p_kws = {k.lower() for k in (p.keyword_set or p.intent_keywords or [])}
            overlap = len(kw_low & p_kws)
            # tie-breaker: Jaccard similarity * 1000
            jacc = int((overlap / len(p_kws)) * 1000) if p_kws else 0
            scored.append((overlap, jacc, p))
        scored.sort(key=lambda t: (-t[0], -t[1], -t[2].confidence_score))
        filtered = [p for ov, _, p in scored if ov > 0]
        return filtered or [p for _, _, p in scored]
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
    """Create a new ParserCache entry if pattern seems valid.
    
    Uses normalized tables: Domain for domain lookup, ParserSample for sample data.
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain_name = parsed.netloc
        
        # Get or create domain record
        domain_record = get_or_create_domain(db, domain_name)
        
        # Compose final stored regex (embed flags inline if provided)
        if flags:
            stored_regex = f"(?{flags}:{pattern})"
        else:
            stored_regex = pattern
        
        parser = ParserCache(
            url_pattern=url,
            domain_id=domain_record.id,
            user_intent=intent.get("target", intent.get("original_input", ""))[:255],
            intent_keywords=intent.get("keywords", [])[:25],
            target_data_type=intent.get("target", "")[:100],
            normalized_intent_hash=hashlib.sha1("|".join(sorted([intent.get("target", ""), *(intent.get("keywords", []) or [])])).encode("utf-8")).hexdigest(),
            keyword_set=sorted({k.lower() for k in (intent.get("keywords") or []) if k})[:50],
            generated_regex=stored_regex,
            source_type=source_type,
            source_identifier=url,
            test_matches_count=matches_count,
            created_by_task_id=task_id,
            confidence_score=100,
            success_rate=100,
        )
        db.add(parser)
        db.flush()  # Get the parser ID
        
        # Create sample record in ParserSample table if sample data provided
        if sample_input or sample_output:
            sample = ParserSample(
                parser_id=parser.id,
                sample_input=(sample_input or "")[:5000],
                sample_output=sample_output[:10] if sample_output else None
            )
            db.add(sample)
        
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

def get_scheduled_jobs(db: Session, owner_id: int) -> List[ScheduledJob]:
    return db.query(ScheduledJob).filter(ScheduledJob.owner_id == owner_id).all()

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
