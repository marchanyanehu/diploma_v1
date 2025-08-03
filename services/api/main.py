"""
Main FastAPI application for the Intelligent Web Data Aggregator.

This module initializes the FastAPI application and defines the core API endpoints
for processing web scraping requests using natural language prompts.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
from typing import Dict, Any

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
        "timestamp": datetime.utcnow().isoformat(),
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
        "timestamp": datetime.utcnow().isoformat(),
        "service": "api",
        "version": "1.0.0",
        "uptime": "operational"
    }


@app.get("/api/v1/health", tags=["Health", "API v1"])
async def api_health_check() -> Dict[str, Any]:
    """
    API v1 health check endpoint.
    
    Returns:
        Dict containing API health status
    """
    return {
        "api_version": "v1",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "process": "/api/v1/process",
            "status": "/api/v1/status/{task_id}",
            "result": "/api/v1/result/{task_id}"
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors with custom response."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "timestamp": datetime.utcnow().isoformat()
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
            "timestamp": datetime.utcnow().isoformat()
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
