"""Lightweight in-process metrics counters.

Counters are incremented in code paths and periodically logged so an
external log scraper can aggregate them. Not thread-safe (single process).
"""
from __future__ import annotations
from typing import Dict
from collections import defaultdict

_counters: Dict[str, int] = defaultdict(int)

def inc(name: str, value: int = 1) -> None:
    _counters[name] += value

def get(name: str) -> int:
    return _counters.get(name, 0)

def snapshot() -> dict[str, int]:  # pragma: no cover
    return dict(_counters)
