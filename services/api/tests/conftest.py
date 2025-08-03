"""
Test configuration and fixtures.

This module provides common test configuration and fixtures
for the FastAPI application test suite.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_scrape_request():
    """Sample scrape request data for testing."""
    return {
        "url": "https://example.com",
        "prompt": "Extract all product names and prices"
    }
