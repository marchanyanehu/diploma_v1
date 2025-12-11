"""Centralized logging configuration for the API service."""

import logging
from typing import Optional

from shared.logging_utils import configure_logging


def setup_logging(level: str, logfile: Optional[str] = None) -> logging.Logger:
    """
    Configure logging with correlation-id support.
    """
    return configure_logging(level=level, logfile=logfile)

