"""
DEPRECATED: API schemas moved to shared.schemas

This module is maintained for backward compatibility only.
Import from shared.schemas instead.
"""

# Re-export everything from shared.schemas for backward compatibility
from shared.schemas import (
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


