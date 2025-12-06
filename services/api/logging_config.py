"""
Centralized logging configuration for the API service.
"""

import logging
from typing import Optional


def setup_logging(level: str, logfile: Optional[str] = None) -> logging.Logger:
    handlers = [logging.StreamHandler()]
    if logfile:
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
    )
    return logging.getLogger(__name__)

