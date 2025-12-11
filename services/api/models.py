"""
DEPRECATED: API schemas moved to services.api.schemas

This module is maintained for backward compatibility only.
Import from .schemas instead.
"""

# Re-export everything from local schemas for backward compatibility
from .schemas import (
    UserCreate,
    UserResponse,
    Token,
    ScrapeRequest,
    TaskResponse,
    TaskStatus,
    TaskStatusResponse,
    ScrapeResult,
    ErrorResponse,
    ScheduledJobCreate,
    ScheduledJobResponse,
)

__all__ = [
    'UserCreate',
    'UserResponse',
    'Token',
    'ScrapeRequest',
    'TaskResponse',
    'TaskStatus',
    'TaskStatusResponse',
    'ScrapeResult',
    'ErrorResponse',
    'ScheduledJobCreate',
    'ScheduledJobResponse',
]


