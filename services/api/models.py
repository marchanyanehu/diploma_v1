from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ScrapeRequest(BaseModel):
    url: HttpUrl
    prompt: str = Field(..., min_length=5, max_length=1000)

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatus(str):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ScrapeResult(BaseModel):
    task_id: str
    status: str
    url: str
    prompt: str
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    processing_time: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime

class ScheduledJobCreate(BaseModel):
    url: HttpUrl
    prompt: str
    schedule_cron: str

class ScheduledJobResponse(BaseModel):
    id: int
    url: str
    prompt: str
    schedule_cron: str
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

