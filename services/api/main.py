"""
Main FastAPI application for the Intelligent Web Data Aggregator.

This module initializes the FastAPI application and defines the core API endpoints
for processing web scraping requests using natural language prompts.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, cast
from uuid import uuid4
import logging, os

# Import database components
from .database import get_db, create_tables
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
from typing import Dict, Any, Optional, cast, List
from . import auth
from . import db_utils
from shared.celery_app import celery_app
try:  # optional import for inline fallback
    from services.headless_worker.tasks import process_request_task  # type: ignore
except Exception:  # noqa: BLE001
    process_request_task = None  # type: ignore

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.getenv("API_LOG_FILE", "api_debug.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

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
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db_utils.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    try:
        hashed_password = auth.get_password_hash(user.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return db_utils.create_user(db=db, username=user.username, password_hash=hashed_password, email=user.email)

@app.post("/auth/token", response_model=Token, tags=["Auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db_utils.get_user_by_username(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Scheduler Endpoints ---

@app.post("/api/v1/jobs", response_model=ScheduledJobResponse, tags=["Scheduler", "API v1"])
def create_job(job: ScheduledJobCreate, db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)):
    return db_utils.create_scheduled_job(db, str(job.url), job.prompt, job.schedule_cron, current_user.id)

@app.get("/api/v1/jobs", response_model=List[ScheduledJobResponse], tags=["Scheduler", "API v1"])
def list_jobs(db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)):
    return db_utils.get_scheduled_jobs(db, current_user.id)

@app.delete("/api/v1/jobs/{job_id}", tags=["Scheduler", "API v1"])
def delete_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(auth.get_current_user)):
    success = db_utils.delete_scheduled_job(db, job_id, current_user.id)
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
    },
)
async def process_request(
    request: ScrapeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> TaskResponse:
    """
    Create a new scraping task for the provided URL and prompt.

    Note: Actual async processing is added in Task #203. For now, we persist
    a PENDING task and return its identifier so clients can poll status later.
    """
    task_id = str(uuid4())
    logger.info("api.process_request.received", extra={"task_id": task_id, "url": str(request.url), "user": current_user.username})
    try:
        # Best-effort persistence; if DB is unavailable, continue gracefully
        db_utils.create_scraping_task(
            db=db,
            task_id=task_id,
            url=str(request.url),
            user_prompt=request.prompt,
            status=TaskStatus.PENDING.value,
            owner_id=current_user.id,
        )
    except Exception as e:
        logger.warning("api.process_request.db_persist_failed", extra={"task_id": task_id, "error": str(e)})

    # Enqueue background processing via Celery (non-blocking)
    try:
        celery_app.send_task(
            "scrape.process_request_full",
            args=[task_id, str(request.url), request.prompt],
            queue="ai_queue", # Updated queue for full process which starts with AI/Analysis or orchestration
        )
        logger.info("api.process_request.enqueued", extra={"task_id": task_id})
    except Exception as e:
        logger.error("api.process_request.enqueue_failed", extra={"task_id": task_id, "error": str(e)})
    # Inline fallback if eager or enqueue failed
    if (os.getenv("CELERY_EAGER") or os.getenv("CELERY_ALWAYS_EAGER")) and process_request_task is not None:
        try:
            logger.info("api.process_request.inline_start", extra={"task_id": task_id})
            process_request_task(task_id, str(request.url), request.prompt)
            logger.info("api.process_request.inline_done", extra={"task_id": task_id})
        except Exception as inline_exc:  # noqa: BLE001
            logger.exception("api.process_request.inline_failed", extra={"task_id": task_id, "error": str(inline_exc)})

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
    current_user: User = Depends(auth.get_current_user)
) -> TaskStatusResponse:
    """
    Retrieve the current status for a scraping task by its task_id.

    If the task is not found, a 404 error is returned. Timestamps are
    provided based on available fields; when missing, sensible defaults
    are applied.
    """
    try:
        task = db_utils.get_scraping_task(db, task_id)
    except Exception as e:
        logger.error(f"Failed to query task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to query task status")

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Ensure user owns the task (or is admin - simplistic check here)
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    # Map DB status string to API enum
    try:
        status_enum = TaskStatus(task.status)
    except ValueError:
        status_enum = TaskStatus.FAILED

    # Extract concrete values from ORM attributes (avoid Column[T] typing)
    task_id_value: str = cast(str, getattr(task, "task_id", ""))
    created_at: datetime = cast(
        datetime, getattr(task, "created_at", None) or datetime.now(timezone.utc)
    )
    # Prefer completed_at, then started_at, else created_at
    updated_at: datetime = cast(
        datetime,
        getattr(task, "completed_at", None)
        or getattr(task, "started_at", None)
        or created_at,
    )

    # Avoid direct truthiness checks on SQLAlchemy columns for type checkers
    err_msg: Optional[str] = cast(Optional[str], getattr(task, "error_message", None))

    return TaskStatusResponse(
        task_id=task_id_value,
        status=status_enum,
        progress=None,
        message=err_msg,
        created_at=created_at,
        updated_at=updated_at,
    )


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
    current_user: User = Depends(auth.get_current_user)
) -> Any:
    """
    Return the final scraping result when the task is SUCCESS. If the task
    is still running, return 202 with current status. If it failed, return 400.
    """
    try:
        task = db_utils.get_scraping_task(db, task_id)
    except Exception as e:
        logger.error(f"Failed to query task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to query task result")

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    # Normalize status enum
    try:
        status_enum = TaskStatus(task.status)
    except ValueError:
        status_enum = TaskStatus.FAILED

    if status_enum in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}:
        created_at: datetime = cast(
            datetime, getattr(task, "created_at", None) or datetime.now(timezone.utc)
        )
        updated_at: datetime = cast(
            datetime,
            getattr(task, "completed_at", None)
            or getattr(task, "started_at", None)
            or created_at,
        )
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

    # SUCCESS path: build ScrapeResult
    url_value: str = cast(str, getattr(task, "url", ""))
    prompt_value: str = cast(str, getattr(task, "user_prompt", ""))
    data_payload = getattr(task, "extracted_data", None) or []
    created_at: datetime = cast(
        datetime, getattr(task, "created_at", None) or datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = cast(Optional[datetime], getattr(task, "completed_at", None))
    processing_seconds: Optional[int] = cast(Optional[int], getattr(task, "processing_time_seconds", None))
    used_cached: bool = bool(getattr(task, "used_cached_parser", False))
    total_matches: Optional[int] = cast(Optional[int], getattr(task, "total_matches", None))
    parser_id: Optional[int] = cast(Optional[int], getattr(task, "used_parser_id", None))

    metadata: Dict[str, Any] = {
        "total_matches": total_matches,
        "used_cached_parser": used_cached,
        "used_parser_id": parser_id,
    }

    return ScrapeResult(
        task_id=cast(str, getattr(task, "task_id", "")),
        status=status_enum,
        url=cast(Any, url_value),
        prompt=prompt_value,
        data=data_payload,  # expected to align with ExtractedData schema when present
        metadata={k: v for k, v in metadata.items() if v is not None},
        processing_time=float(processing_seconds) if processing_seconds is not None else None,
        created_at=created_at,
        completed_at=completed_at,
    )


@app.post("/api/v1/test-task", tags=["Testing", "API v1"])
async def create_test_task(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Test endpoint to create a sample scraping task.
    
    This endpoint is for testing database connectivity and basic CRUD operations.
    """
    try:
        # Create a test task
        task = db_utils.create_scraping_task(
            db=db,
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


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors with custom response."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors with custom response."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
