"""
Correlation ID utilities shared across services.

Provides helpers to set, get, and propagate correlation identifiers across
HTTP requests and Celery tasks so logs can be stitched end-to-end.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Mapping, Optional

_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id(default: str = "-") -> str:
    """Return the current correlation id or a default placeholder."""
    cid = _correlation_id.get()
    return cid or default


def set_correlation_id(value: Optional[str] = None) -> str:
    """
    Set the correlation id, generating one if not provided.

    Returns the correlation id that was set.
    """
    cid = value or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def bind_from_headers(headers: Optional[Mapping[str, str]]) -> str:
    """
    Extract correlation id from incoming headers (Celery/HTTP) and bind it.
    Falls back to generating a new id if none is present.
    """
    if headers:
        cid = (
            headers.get("correlation_id")
            or headers.get("Correlation-Id")
            or headers.get("X-Correlation-Id")
        )
        if cid:
            return set_correlation_id(cid)
    return set_correlation_id()


def correlation_extra(extra: Optional[dict] = None) -> dict:
    """Convenience to attach correlation id into logging extra payloads."""
    payload = extra.copy() if extra else {}
    payload["correlation_id"] = get_correlation_id()
    return payload

