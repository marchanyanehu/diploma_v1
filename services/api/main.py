"""
Main FastAPI application for the Intelligent Web Data Aggregator.

This module initializes the FastAPI application and defines the core API endpoints
for processing web scraping requests using natural language prompts.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime, timezone
from typing import Dict, Any, Optional, cast
from uuid import uuid4
import logging

# Import database components
from .database import get_db, create_tables
from .db_models import ScrapingTask, ParserCache
from .models import ScrapeRequest, TaskResponse, TaskStatus, TaskStatusResponse
from . import db_utils
from shared.celery_app import celery_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
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
        "email": "yan.marchan@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup."""
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.warning(f"Database not available: {e}")
        logger.info("Running in development mode without database")


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
)
async def process_request(
    request: ScrapeRequest,
    db: Session = Depends(get_db),
) -> TaskResponse:
    """
    Create a new scraping task for the provided URL and prompt.

    Note: Actual async processing is added in Task #203. For now, we persist
    a PENDING task and return its identifier so clients can poll status later.
    """
    task_id = str(uuid4())
    try:
        # Best-effort persistence; if DB is unavailable, continue gracefully
        db_utils.create_scraping_task(
            db=db,
            task_id=task_id,
            url=str(request.url),
            user_prompt=request.prompt,
            status=TaskStatus.PENDING.value,
        )
    except Exception as e:
        logger.warning(f"DB unavailable or failed to persist task {task_id}: {e}")

    # Enqueue background processing via Celery (non-blocking)
    try:
        celery_app.send_task(
            "scrape.process_request",
            args=[task_id, str(request.url), request.prompt],
            queue="default",
        )
        logger.info(f"Enqueued Celery task for {task_id}")
    except Exception as e:
        # If queuing fails, we still return PENDING so client can retry later
        logger.error(f"Failed to enqueue Celery task for {task_id}: {e}")

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created successfully",
    )


@app.get(
    "/api/v1/status/{task_id}",
    response_model=TaskStatusResponse,
    tags=["API v1"],
    summary="Get task status",
    description=(
        "Check the current status of a previously created task. Returns one of "
        "PENDING, IN_PROGRESS, SUCCESS, or FAILED."
    ),
)
async def get_task_status(task_id: str, db: Session = Depends(get_db)) -> TaskStatusResponse:
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
