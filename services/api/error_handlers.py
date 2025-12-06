"""
Centralized error handlers to keep FastAPI app setup slim.
"""

from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI


async def not_found_handler(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def internal_error_handler(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(404, not_found_handler)
    app.add_exception_handler(500, internal_error_handler)

