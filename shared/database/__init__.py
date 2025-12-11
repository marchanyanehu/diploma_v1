"""
Shared database module for the Intelligent Web Data Aggregator.

This module provides database configuration, models, and utilities
that are shared across all services (API, workers, scheduler).
"""

from .connection import (
    Base,
    engine,
    SessionLocal,
    get_db,
    create_tables,
    drop_tables,
)

from .models import (
    User,
    Domain,
    ScrapingTask,
    TaskSourceData,
    TaskIntent,
    ParserCache,
    ParserSample,
    ScheduledJob,
)

from .utils import (
    get_or_create_domain,
    create_user,
    get_user_by_username,
    create_scraping_task,
    get_scraping_task,
    update_task_status,
    update_task_sources,
    persist_extraction_result,
    find_cached_parser_by_fields,
    create_parser_cache_by_fields,
    update_parser_usage,
    invalidate_parser,
    create_scheduled_job,
    get_scheduled_jobs_by_user,
    get_due_jobs,
    delete_scheduled_job,
)

__all__ = [
    # Connection
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "create_tables",
    "drop_tables",
    # Models
    "User",
    "Domain",
    "ScrapingTask",
    "TaskSourceData",
    "TaskIntent",
    "ParserCache",
    "ParserSample",
    "ScheduledJob",
    # Utils
    "get_or_create_domain",
    "create_user",
    "get_user_by_username",
    "create_scraping_task",
    "get_scraping_task",
    "update_task_status",
    "update_task_sources",
    "persist_extraction_result",
    "find_cached_parser_by_fields",
    "create_parser_cache_by_fields",
    "update_parser_usage",
    "invalidate_parser",
    "create_scheduled_job",
    "get_scheduled_jobs_by_user",
    "get_due_jobs",
    "delete_scheduled_job",
]
