"""
Global test configuration and fixtures.

This file provides shared pytest fixtures for the test suite.
It also ensures the repository root is on sys.path so that the
`services` package can be imported when running tests locally.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure repo root is importable (so `services` package resolves)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)
