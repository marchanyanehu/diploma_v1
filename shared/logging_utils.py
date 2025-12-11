"""
Shared logging configuration with correlation-id support.
"""

from __future__ import annotations

import logging
from typing import Optional

from .correlation import get_correlation_id


class CorrelationIdFilter(logging.Filter):
    """Inject correlation_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - simple filter
        record.correlation_id = get_correlation_id()
        return True


def configure_logging(level: str = "INFO", logfile: Optional[str] = None) -> logging.Logger:
    """
    Configure root logging with correlation-id field.

    Safe to call multiple times; only first call to basicConfig takes effect.
    """
    handlers = [logging.StreamHandler()]
    if logfile:
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s [cid=%(correlation_id)s] %(message)s",
        handlers=handlers,
    )

    for handler in logging.getLogger().handlers:
        handler.addFilter(CorrelationIdFilter())

    return logging.getLogger(__name__)

