"""
Pydantic models for API request and response validation.

This module defines the data models used for API endpoints,
ensuring proper validation and serialization of requests and responses.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


# Shared example constants to keep docs consistent
EXAMPLE_URL = "https://example-jobs.com"
EXAMPLE_PROMPT = "I want all the job listings with their titles and locations"
EXAMPLE_XPATH = "//div[@class='job-card']/h2"


class TaskStatus(str, Enum):
    """Enumeration of possible task statuses."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ScrapeRequest(BaseModel):
    """Request model for the scraping endpoint."""
    
    url: HttpUrl = Field(
        description="The URL to scrape data from",
    examples=[EXAMPLE_URL]
    )
    prompt: str = Field(
        min_length=5,
        max_length=500,
        description="Natural language description of the data to extract",
    examples=[EXAMPLE_PROMPT]
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "url": EXAMPLE_URL,
                "prompt": EXAMPLE_PROMPT
            }
        }
    }


class TaskResponse(BaseModel):
    """Response model for task creation."""
    
    task_id: str = Field(
        description="Unique identifier for the created task",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    status: TaskStatus = Field(
        description="Current status of the task",
        examples=[TaskStatus.PENDING]
    )
    message: str = Field(
        default="Task created successfully",
        description="Human-readable message about the task creation"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the task was created"
    )


class TaskStatusResponse(BaseModel):
    """Response model for task status queries."""
    
    task_id: str = Field(
        description="Task identifier",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    status: TaskStatus = Field(
        description="Current status of the task"
    )
    progress: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Task progress percentage (0-100)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Status message or error description"
    )
    created_at: datetime = Field(
        description="Timestamp when the task was created"
    )
    updated_at: datetime = Field(
        description="Timestamp when the status was last updated"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "IN_PROGRESS",
                "progress": 60,
                "message": None,
                "created_at": "2025-08-08T12:00:00Z",
                "updated_at": "2025-08-08T12:00:30Z"
            }
        }
    }


class ExtractedData(BaseModel):
    """Model for extracted data items."""
    
    text: str = Field(
        description="The extracted text content"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source information (HTML element, JSON path, etc.)"
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the extraction (0.0-1.0)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Senior Software Engineer — Berlin",
                "source": EXAMPLE_XPATH,
                "confidence": 0.92
            }
        }
    }


class ScrapeResult(BaseModel):
    """Response model for successful scraping results."""
    
    task_id: str = Field(
        description="Task identifier"
    )
    status: TaskStatus = Field(
        description="Final task status"
    )
    url: HttpUrl = Field(
        description="The scraped URL"
    )
    prompt: str = Field(
        description="The original extraction prompt"
    )
    data: List[ExtractedData] = Field(
        default=[],
        description="List of extracted data items"
    )
    metadata: Dict[str, Any] = Field(
        default={},
        description="Additional metadata about the scraping process"
    )
    processing_time: Optional[float] = Field(
        default=None,
        description="Total processing time in seconds"
    )
    created_at: datetime = Field(
        description="Task creation timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Task completion timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "SUCCESS",
                "url": EXAMPLE_URL,
                "prompt": EXAMPLE_PROMPT,
                "data": [
                    {
                        "text": "Senior Software Engineer — Berlin",
                        "source": EXAMPLE_XPATH,
                        "confidence": 0.92
                    },
                    {
                        "text": "Data Scientist — Remote",
                        "source": EXAMPLE_XPATH,
                        "confidence": 0.88
                    }
                ],
                "metadata": {
                    "total_matches": 2,
                    "used_cached_parser": False,
                    "used_parser_id": None
                },
                "processing_time": 3.21,
                "created_at": "2025-08-08T12:00:00Z",
                "completed_at": "2025-08-08T12:00:03Z"
            }
        }
    }


class ErrorResponse(BaseModel):
    """Response model for API errors."""
    
    error: str = Field(
        description="Error type or code"
    )
    message: str = Field(
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Error occurrence timestamp"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""
    
    status: str = Field(
        default="healthy",
        description="Service health status"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Health check timestamp"
    )
    version: str = Field(
        default="1.0.0",
        description="API version"
    )
    uptime: Optional[str] = Field(
        default=None,
        description="Service uptime information"
    )
