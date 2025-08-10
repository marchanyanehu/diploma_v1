"""
Database service layer for handling database operations.

This module provides higher-level functions for interacting with the database,
including CRUD operations and business logic for scraping tasks and parser cache.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import logging
from urllib.parse import urlparse

from .db_models import ScrapingTask, ParserCache
from .database import get_db

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service class for database operations."""
    
    def __init__(self, db: Session):
        """
        Initialize the database service.
        
        Args:
            db: Database session from FastAPI dependency injection
        """
        self.db = db
    
    # Scraping Task CRUD Operations
    
    def create_scraping_task(
        self,
        task_id: str,
        url: str,
        user_prompt: str,
        status: str = "PENDING"
    ) -> ScrapingTask:
        """
        Create a new scraping task.
        
        Args:
            task_id: Unique task identifier
            url: URL to scrape
            user_prompt: User's natural language prompt
            status: Initial task status
            
        Returns:
            Created ScrapingTask instance
        """
        task = ScrapingTask(
            task_id=task_id,
            url=url,
            user_prompt=user_prompt,
            status=status
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        logger.info(f"Created scraping task: {task_id}")
        return task
    
    def get_scraping_task(self, task_id: str) -> Optional[ScrapingTask]:
        """
        Get a scraping task by task_id.
        
        Args:
            task_id: Task identifier
            
        Returns:
            ScrapingTask instance or None if not found
        """
        return self.db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).first()
    
    def update_scraping_task_status(
        self,
        task_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[ScrapingTask]:
        """
        Update the status of a scraping task.
        
        Args:
            task_id: Task identifier
            status: New status
            error_message: Optional error message for failed tasks
            
        Returns:
            Updated ScrapingTask instance or None if not found
        """
        task = self.get_scraping_task(task_id)
        if not task:
            return None
        
        task.status = status
        if error_message:
            task.error_message = error_message
        
        # Update timestamps based on status
    now = datetime.now(timezone.utc)
        if status == "IN_PROGRESS" and not task.started_at:
            task.started_at = now
        elif status in ["SUCCESS", "FAILED"]:
            task.completed_at = now
            if task.started_at:
                task.processing_time_seconds = int((now - task.started_at).total_seconds())
        
        self.db.commit()
        self.db.refresh(task)
        logger.info(f"Updated task {task_id} status to {status}")
        return task
    
    def update_scraping_task_results(
        self,
        task_id: str,
        extracted_data: Optional[List[Dict[str, Any]]] = None,
        total_matches: Optional[int] = None,
        page_content: Optional[str] = None,
        network_requests: Optional[List[Dict[str, Any]]] = None,
        used_cached_parser: bool = False,
        parser_id: Optional[int] = None
    ) -> Optional[ScrapingTask]:
        """
        Update the results of a scraping task.
        
        Args:
            task_id: Task identifier
            extracted_data: Extracted data results
            total_matches: Number of matches found
            page_content: Raw page content
            network_requests: Captured network requests
            used_cached_parser: Whether a cached parser was used
            parser_id: ID of the parser used (if any)
            
        Returns:
            Updated ScrapingTask instance or None if not found
        """
        task = self.get_scraping_task(task_id)
        if not task:
            return None
        
        if extracted_data is not None:
            task.extracted_data = extracted_data
        if total_matches is not None:
            task.total_matches = total_matches
        if page_content is not None:
            task.page_content = page_content
        if network_requests is not None:
            task.network_requests = network_requests
        
        task.used_cached_parser = used_cached_parser
        if parser_id:
            task.used_parser_id = parser_id
        
        self.db.commit()
        self.db.refresh(task)
        logger.info(f"Updated task {task_id} results")
        return task
    
    # Parser Cache CRUD Operations
    
    def create_parser_cache(
        self,
        url_pattern: str,
        user_intent: str,
        generated_regex: str,
        source_type: str,
        created_by_task_id: str,
        test_matches_count: int,
        domain: Optional[str] = None,
        source_identifier: Optional[str] = None,
        intent_keywords: Optional[List[str]] = None,
        target_data_type: Optional[str] = None,
        llm_model_used: Optional[str] = None,
        generation_attempts: int = 1,
        sample_input: Optional[str] = None,
        sample_output: Optional[List[Dict[str, Any]]] = None
    ) -> ParserCache:
        """
        Create a new parser cache entry.
        
        Args:
            url_pattern: URL pattern or exact URL
            user_intent: User's intent/prompt
            generated_regex: Working regular expression
            source_type: Type of source (HTML, JSON, etc.)
            created_by_task_id: Task that created this parser
            test_matches_count: Number of matches during validation
            domain: Extracted domain (auto-extracted if not provided)
            source_identifier: Source identifier (XHR URL, selector, etc.)
            intent_keywords: Keywords extracted from intent
            target_data_type: Type of target data
            llm_model_used: LLM model used for generation
            generation_attempts: Number of generation attempts
            sample_input: Sample input used for generation
            sample_output: Sample expected output
            
        Returns:
            Created ParserCache instance
        """
        # Auto-extract domain if not provided
        if not domain:
            try:
                parsed_url = urlparse(url_pattern)
                domain = parsed_url.netloc
            except Exception:
                domain = "unknown"
        
        parser = ParserCache(
            url_pattern=url_pattern,
            domain=domain,
            user_intent=user_intent,
            generated_regex=generated_regex,
            source_type=source_type,
            created_by_task_id=created_by_task_id,
            test_matches_count=test_matches_count,
            source_identifier=source_identifier,
            intent_keywords=intent_keywords,
            target_data_type=target_data_type,
            llm_model_used=llm_model_used,
            generation_attempts=generation_attempts,
            sample_input=sample_input,
            sample_output=sample_output
        )
        
        self.db.add(parser)
        self.db.commit()
        self.db.refresh(parser)
        logger.info(f"Created parser cache for domain: {domain}")
        return parser
    
    def find_cached_parser(
        self,
        url: str,
        user_intent: str,
        confidence_threshold: int = 70
    ) -> Optional[ParserCache]:
        """
        Find a cached parser that matches the URL and user intent.
        
        Args:
            url: Target URL
            user_intent: User's intent/prompt
            confidence_threshold: Minimum confidence score
            
        Returns:
            Matching ParserCache instance or None if not found
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # First try exact URL match
        exact_match = (
            self.db.query(ParserCache)
            .filter(
                and_(
                    ParserCache.url_pattern == url,
                    ParserCache.confidence_score >= confidence_threshold
                )
            )
            .order_by(ParserCache.confidence_score.desc(), ParserCache.last_used_at.desc())
            .first()
        )
        
        if exact_match:
            logger.info(f"Found exact URL match for parser: {exact_match.id}")
            return exact_match
        
        # Then try domain-based matching with intent similarity
        domain_matches = (
            self.db.query(ParserCache)
            .filter(
                and_(
                    ParserCache.domain == domain,
                    ParserCache.confidence_score >= confidence_threshold
                )
            )
            .order_by(ParserCache.confidence_score.desc(), ParserCache.last_used_at.desc())
            .all()
        )
        
        # Simple intent matching (can be improved with semantic similarity)
        user_intent_lower = user_intent.lower()
        for parser in domain_matches:
            cached_intent_lower = parser.user_intent.lower()
            
            # Check for keyword overlap (simplified matching)
            user_words = set(user_intent_lower.split())
            cached_words = set(cached_intent_lower.split())
            overlap = len(user_words.intersection(cached_words))
            
            # If there's significant overlap, consider it a match
            if overlap >= min(3, len(user_words) // 2):
                logger.info(f"Found domain+intent match for parser: {parser.id}")
                return parser
        
        logger.info(f"No cached parser found for {domain}")
        return None
    
    def update_parser_usage_stats(
        self,
        parser_id: int,
        success: bool = True
    ) -> Optional[ParserCache]:
        """
        Update usage statistics for a parser.
        
        Args:
            parser_id: Parser ID
            success: Whether the parser worked successfully
            
        Returns:
            Updated ParserCache instance or None if not found
        """
        parser = self.db.query(ParserCache).filter(ParserCache.id == parser_id).first()
        if not parser:
            return None
        
        # Update usage stats
        old_times_used = parser.times_used or 0
        old_success_rate = parser.success_rate or 100
        old_confidence = parser.confidence_score or 100
        
        parser.times_used = old_times_used + 1
    parser.last_used_at = datetime.now(timezone.utc)
        
        if success:
            # Maintain or slightly increase confidence
            parser.confidence_score = min(100, old_confidence + 1)
        else:
            # Decrease confidence on failure
            parser.confidence_score = max(0, old_confidence - 10)
        
        # Recalculate success rate
        if parser.times_used > 0:
            successful_uses = int((old_success_rate / 100) * old_times_used)
            if success:
                successful_uses += 1
            parser.success_rate = int((successful_uses / parser.times_used) * 100)
        
        self.db.commit()
        self.db.refresh(parser)
        logger.info(f"Updated parser {parser_id} usage stats (success: {success})")
        return parser
    
    def get_parser_by_id(self, parser_id: int) -> Optional[ParserCache]:
        """
        Get a parser by ID.
        
        Args:
            parser_id: Parser ID
            
        Returns:
            ParserCache instance or None if not found
        """
        return self.db.query(ParserCache).filter(ParserCache.id == parser_id).first()
    
    def get_recent_tasks(self, limit: int = 10) -> List[ScrapingTask]:
        """
        Get recent scraping tasks.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of recent ScrapingTask instances
        """
        return (
            self.db.query(ScrapingTask)
            .order_by(ScrapingTask.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def get_parser_stats(self) -> Dict[str, Any]:
        """
        Get statistics about cached parsers.
        
        Returns:
            Dictionary with parser statistics
        """
        total_parsers = self.db.query(ParserCache).count()
        
        # High confidence parsers (>= 80)
        high_confidence = (
            self.db.query(ParserCache)
            .filter(ParserCache.confidence_score >= 80)
            .count()
        )
        
        # Recently used parsers (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recently_used = (
            self.db.query(ParserCache)
            .filter(ParserCache.last_used_at >= week_ago)
            .count()
        )
        
        # Most popular domains
        popular_domains = (
            self.db.query(ParserCache.domain, func.count(ParserCache.id))
            .group_by(ParserCache.domain)
            .order_by(func.count(ParserCache.id).desc())
            .limit(5)
            .all()
        )
        
        return {
            "total_parsers": total_parsers,
            "high_confidence_parsers": high_confidence,
            "recently_used_parsers": recently_used,
            "popular_domains": [{"domain": domain, "count": count} for domain, count in popular_domains]
        }
