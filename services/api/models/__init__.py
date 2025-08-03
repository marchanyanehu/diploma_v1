"""
Pydantic models for API request and response validation.

This module defines the data models used for API endpoints,
ensuring proper validation and serialization of requests and responses.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


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
        examples=["https://example-jobs.com"]
    )
    prompt: str = Field(
        min_length=5,
        max_length=500,
        description="Natural language description of the data to extract",
        examples=["I want all the job listings with their titles and locations"]
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://example-jobs.com",
                "prompt": "I want all the job listings with their titles and locations"
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
        default_factory=datetime.utcnow,
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
        default_factory=datetime.utcnow,
        description="Error occurrence timestamp"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""
    
    status: str = Field(
        default="healthy",
        description="Service health status"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
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
