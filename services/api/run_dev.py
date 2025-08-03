#!/usr/bin/env python3
"""
Development runner for the FastAPI application.

This script provides a convenient way to run the FastAPI application
in development mode with auto-reload and proper configuration.
"""

import uvicorn
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
        access_log=True
    )
