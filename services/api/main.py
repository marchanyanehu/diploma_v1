"""
Main FastAPI application for the Intelligent Web Data Aggregator.

This module initializes the FastAPI application and defines the core API endpoints
for processing web scraping requests using natural language prompts.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, cast, List
import logging

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Input sanitization
from shared.input_sanitization import sanitize_user_input, InputSanitizationError

# Import database components
from .database import get_db, create_tables
from .config import settings
from .logging_config import setup_logging
from .error_handlers import register_error_handlers
from .db_models import ScrapingTask, ParserCache, User
from .models import (
    ScrapeRequest,
    TaskResponse,
    TaskStatus,
    TaskStatusResponse,
    ScrapeResult,
    ErrorResponse,
    UserCreate,
    Token,
    UserResponse,
    ScheduledJobCreate,
    ScheduledJobResponse,
)
from . import auth
from shared.celery_app import celery_app
from .services.task_service import (
    TaskService,
    CeleryTaskQueue,
    TaskNotFoundError,
    TaskForbiddenError,
)
from .services.auth_service import AuthService
from .services import task_presenter
from .repositories import UserRepository, TaskRepository, ScheduleRepository
try:  # optional import for inline fallback
    from services.headless_worker.tasks import process_request_task  # type: ignore
except Exception:  # noqa: BLE001
    process_request_task = None  # type: ignore

# Configure logging centrally
logger = setup_logging(settings.log_level, settings.api_log_file)

# Initialize rate limiter
# Uses Redis if available (via REDIS_URL), falls back to in-memory storage
def _get_rate_limit_storage_uri() -> str | None:
    """Determine storage URI for rate limiter.
    
    Returns Redis URL if available, otherwise None (in-memory storage).
    In test/dev environments without Redis, uses in-memory storage.
    """
    import os
    # Skip Redis in test environment
    if os.getenv("TESTING", "").lower() in ("1", "true", "yes"):
        return "memory://"
    
    redis_url = getattr(settings, 'redis_url', None)
    if redis_url and redis_url != "redis://localhost:6379/0":
        return redis_url
    
    # Try to ping Redis before using it
    try:
        import redis
        r = redis.from_url(redis_url or "redis://localhost:6379/0", socket_timeout=1)
        r.ping()
        return redis_url
    except Exception:
        logger.info("Redis unavailable for rate limiting, using in-memory storage")
        return "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Global default
    storage_uri=_get_rate_limit_storage_uri(),
)

# Initialize FastAPI app
tags_metadata = [
    {
        "name": "Root",
        "description": "Basic information and navigation for the API.",
    },
    {
        "name": "Health",
        "description": "Liveness and readiness probes, including DB connectivity checks.",
    },
    {
        "name": "Auth",
        "description": "Authentication endpoints (login, register).",
    },
    {
        "name": "API v1",
        "description": "Primary public API for creating scraping tasks, tracking status, and retrieving results.",
    },
    {
        "name": "Testing",
        "description": "Non-production helpers used during development and CI.",
    },
]

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[override]
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Database not available: {e}")
        logger.info("Running in development mode without database")
    yield


app = FastAPI(
    title="Intelligent Web Data Aggregator",
    description="""
    An intelligent service that accepts a URL and a natural language prompt 
    and automatically extracts the requested data using web scraping and 
    Large Language Models (LLMs).
    
    ## Features
    
    * **Natural Language Processing**: Use plain English to describe what data you want
    * **Intelligent Extraction**: LLM-powered data identification and extraction
    * **Regex Generation**: Automatic regular expression creation and validation
    * **Caching**: Smart caching of successful parsers for future use
    * **Asynchronous Processing**: Non-blocking task execution with status tracking
    """,
    version="1.0.0",
    contact={
        "name": "Yan Marchan",
        "email": "dadada.marchan@gmail.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    """Provide TaskService with injected dependencies (DIP)."""
    queue = CeleryTaskQueue(celery_app)
    task_repo = TaskRepository(db)
    return TaskService(db=db, queue=queue, fallback_task=process_request_task, task_repo=task_repo)


def get_task_repo(db: Session = Depends(get_db)) -> TaskRepository:
    return TaskRepository(db)


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_schedule_repo(db: Session = Depends(get_db)) -> ScheduleRepository:
    return ScheduleRepository(db)


## Startup hook replaced by lifespan


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing basic API information.
    
    Returns:
        Dict containing API information and status
    """
    return {
        "message": "Intelligent Web Data Aggregator API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "documentation": "/docs",
        "health_check": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Dict containing health status and system information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "api",
        "version": "1.0.0",
        "uptime": "operational"
    }


@app.get("/api/v1/health", tags=["Health", "API v1"])
async def api_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    API v1 health check endpoint with database connectivity test.
    
    Returns:
        Dict containing API health status and database connectivity
    """
    # Test database connectivity
    try:
        # Simple query to test database connection
        task_count = db.query(ScrapingTask).count()
        parser_count = db.query(ParserCache).count()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_status = "disconnected"
        task_count = parser_count = -1
    
    return {
        "api_version": "v1",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "status": db_status,
            "tasks_count": task_count,
            "parsers_count": parser_count
        },
        "endpoints": {
            "process": "/api/v1/process",
            "status": "/api/v1/status/{task_id}",
            "result": "/api/v1/result/{task_id}"
        }
    }

# --- Auth Endpoints ---

@app.post("/auth/register", response_model=UserResponse, tags=["Auth"])
@limiter.limit("5/minute")  # Limit registration attempts
def register(
    request: Request,
    user: UserCreate,
    user_repo: UserRepository = Depends(get_user_repo),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    db_user = user_repo.get_by_username(username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    try:
        hashed_password = auth_service.hash_password(user.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return user_repo.create(username=user.username, password_hash=hashed_password, email=user.email)

@app.post("/auth/token", response_model=Token, tags=["Auth"])
@limiter.limit("10/minute")  # Limit login attempts to prevent brute force
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepository = Depends(get_user_repo),
    auth_service: auth.AuthService = Depends(auth.get_auth_service),
):
    user = user_repo.get_by_username(form_data.username)
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(user.username, access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# --- Scheduler Endpoints ---

@app.post("/api/v1/jobs", response_model=ScheduledJobResponse, tags=["Scheduler", "API v1"])
def create_job(
    job: ScheduledJobCreate,
    schedule_repo: ScheduleRepository = Depends(get_schedule_repo),
    current_user: User = Depends(auth.get_current_user),
):
    return schedule_repo.create(str(job.url), job.prompt, job.schedule_cron, current_user.id)

@app.get("/api/v1/jobs", response_model=List[ScheduledJobResponse], tags=["Scheduler", "API v1"])
def list_jobs(
    schedule_repo: ScheduleRepository = Depends(get_schedule_repo),
    current_user: User = Depends(auth.get_current_user),
):
    return schedule_repo.list_for_owner(current_user.id)

@app.delete("/api/v1/jobs/{job_id}", tags=["Scheduler", "API v1"])
def delete_job(
    job_id: int,
    schedule_repo: ScheduleRepository = Depends(get_schedule_repo),
    current_user: User = Depends(auth.get_current_user),
):
    success = schedule_repo.delete_for_owner(job_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted"}

# --- Core API Endpoints ---

@app.post(
    "/api/v1/process",
    response_model=TaskResponse,
    status_code=202,
    tags=["API v1"],
    summary="Create a scraping task",
    description=(
        "Accepts a URL and a natural language prompt, creates a background scraping "
        "task (initially PENDING), and returns its task_id for status polling."
    ),
    responses={
        202: {
            "description": "Task accepted and created",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "PENDING",
                        "message": "Task created successfully",
                        "created_at": "2025-08-08T12:00:00Z"
                    }
                }
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "Validation error in the request body",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Bad Request",
                        "message": "Invalid URL format",
                        "timestamp": "2025-08-08T12:00:00Z"
                    }
                }
            },
        },
        401: {"description": "Not authenticated"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")  # Limit scraping requests to prevent abuse
async def process_request(
    request: Request,
    scrape_request: ScrapeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Create a new scraping task for the provided URL and prompt.

    Note: Actual async processing is added in Task #203. For now, we persist
    a PENDING task and return its identifier so clients can poll status later.
    """
    # Sanitize user input to prevent prompt injection
    try:
        sanitized_prompt = sanitize_user_input(scrape_request.prompt)
    except InputSanitizationError as e:
        logger.warning(
            "api.process_request.blocked_injection",
            extra={"user": current_user.username, "reason": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid prompt: {e}",
        )
    
    logger.info(
        "api.process_request.received",
        extra={"url": str(scrape_request.url), "user": current_user.username},
    )
    task_id = task_service.create_task(str(scrape_request.url), sanitized_prompt, current_user.id)
    resp = TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created successfully",
    )
    logger.info("api.process_request.accepted", extra={"task_id": task_id})
    return resp


@app.get(
    "/api/v1/status/{task_id}",
    response_model=TaskStatusResponse,
    tags=["API v1"],
    summary="Get task status",
    description=(
        "Check the current status of a previously created task. Returns one of "
        "PENDING, IN_PROGRESS, SUCCESS, or FAILED."
    ),
    responses={
        200: {
            "description": "Current task status",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "IN_PROGRESS",
                        "progress": 40,
                        "message": None,
                        "created_at": "2025-08-08T12:00:00Z",
                        "updated_at": "2025-08-08T12:00:20Z"
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "Task not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Not Found",
                        "message": "Task not found",
                        "timestamp": "2025-08-08T12:00:00Z"
                    }
                }
            },
        },
        401: {"description": "Not authenticated"},
    },
)
async def get_task_status(
    task_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskStatusResponse:
    """
    Retrieve the current status for a scraping task by its task_id.

    If the task is not found, a 404 error is returned. Timestamps are
    provided based on available fields; when missing, sensible defaults
    are applied.
    """
    try:
        task = task_service.get_task_for_user(task_id, current_user.id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except TaskForbiddenError:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    except Exception as e:
        logger.error(f"Failed to query task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to query task status")

    return task_presenter.build_status_response(task)


@app.get(
    "/api/v1/result/{task_id}",
    response_model=ScrapeResult,
    tags=["API v1"],
    summary="Get final result for a completed task",
    description=(
        "Retrieve the final extracted data for a task once it has completed successfully."
    ),
    responses={
        200: {
            "description": "Successful scraping result",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "SUCCESS",
                        "url": "https://example-jobs.com",
                        "prompt": "I want all the job listings with their titles and locations",
                        "data": [
                            {"text": "Senior Software Engineer — Berlin", "source": "//div[@class='job-card']/h2", "confidence": 0.92}
                        ],
                        "metadata": {"total_matches": 1, "used_cached_parser": False},
                        "processing_time": 3.21,
                        "created_at": "2025-08-08T12:00:00Z",
                        "completed_at": "2025-08-08T12:00:03Z"
                    }
                }
            },
        },
        202: {
            "model": TaskStatusResponse,
            "description": "Task not completed yet",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "IN_PROGRESS",
                        "progress": 75,
                        "message": None,
                        "created_at": "2025-08-08T12:00:00Z",
                        "updated_at": "2025-08-08T12:00:10Z"
                    }
                }
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "Task failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Bad Request",
                        "message": "Task failed: regex did not match",
                        "timestamp": "2025-08-08T12:00:10Z"
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "Task not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Not Found",
                        "message": "Task not found",
                        "timestamp": "2025-08-08T12:00:10Z"
                    }
                }
            },
        },
        401: {"description": "Not authenticated"},
    },
)
async def get_task_result(
    task_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> Any:
    """
    Return the final scraping result when the task is SUCCESS. If the task
    is still running, return 202 with current status. If it failed, return 400.
    """
    try:
        task = task_service.get_task_for_user(task_id, current_user.id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except TaskForbiddenError:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    except Exception as e:
        logger.error(f"Failed to query task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to query task result")

    status_enum = task_presenter.normalize_status(task)

    if status_enum in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}:
        created_at, updated_at = task_presenter.extract_timestamps(task)
        # Return 202 with status payload
        return JSONResponse(
            status_code=202,
            content=TaskStatusResponse(
                task_id=cast(str, getattr(task, "task_id", "")),
                status=status_enum,
                progress=None,
                message=None,
                created_at=created_at,
                updated_at=updated_at,
            ).model_dump(),
        )

    if status_enum is TaskStatus.FAILED:
        err_msg: Optional[str] = cast(Optional[str], getattr(task, "error_message", None))
        raise HTTPException(status_code=400, detail=f"Task failed: {err_msg or 'unspecified error'}")

    return task_presenter.build_result_response(task)


@app.post("/api/v1/test-task", tags=["Testing", "API v1"])
async def create_test_task(task_repo: TaskRepository = Depends(get_task_repo)) -> Dict[str, Any]:
    """
    Test endpoint to create a sample scraping task.
    
    This endpoint is for testing database connectivity and basic CRUD operations.
    """
    try:
        # Create a test task
        task = task_repo.create(
            task_id=f"test-{datetime.now(timezone.utc).isoformat()}",
            url="https://example.com",
            user_prompt="Test task for database verification",
            status="PENDING"
        )
        
        return {
            "message": "Test task created successfully",
            "task": {
                "id": task.id,
                "task_id": task.task_id,
                "url": task.url,
                "user_prompt": task.user_prompt,
                "status": task.status,
                "created_at": task.created_at.isoformat() if task.created_at is not None else None
            }
        }
    except Exception as e:
        logger.error(f"Failed to create test task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create test task: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
