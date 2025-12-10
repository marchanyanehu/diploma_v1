
import pytest
from unittest.mock import patch, MagicMock
from services.ai_worker.tasks import process_request_full
from services.api import db_utils

# We don't need a real DB for this test if we mock SessionLocal correctly.
# Or we can use an in-memory DB.

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    mock_session = MagicMock()
    # Setup mock behavior if needed, e.g. query returns
    return mock_session

@patch("services.ai_worker.tasks.SessionLocal")
@patch("services.ai_worker.tasks.celery_app.send_task")
@patch("services.ai_worker.tasks.extract_intent")
@patch("services.ai_worker.tasks.db_utils")
def test_process_request_full_persistence(mock_db_utils, mock_extract_intent, mock_send_task, mock_session_cls, mock_db_session):
    # Setup mocks
    mock_session_cls.return_value = mock_db_session
    mock_extract_intent.return_value = {"target": "jobs", "keywords": ["python"]}
    
    # Mock db_utils.create_scraping_task to return a mock task object
    mock_task = MagicMock()
    mock_task.status = "PENDING"
    mock_db_utils.create_scraping_task.return_value = mock_task
    mock_db_utils.get_scraping_task.return_value = mock_task
    
    # Run function
    result = process_request_full("task_p1", "http://example.com", "find jobs")
    
    assert result["status"] == "IN_PROGRESS"
    assert "Delegated" in result["message"]
    
    # Verify DB interactions
    # 1. create_scraping_task called? No, process_request_full assumes task exists or creates it?
    # Let's check implementation. It calls get_scraping_task first.
    
    # Verify status update
    # assert mock_task.status == "STARTED" # This fails because mock doesn't update itself unless side_effect is set
    mock_db_utils.update_task_status.assert_any_call(mock_db_session, task_id="task_p1", status="STARTED")
    
    # Verify delegation
    mock_send_task.assert_called_once()
    args = mock_send_task.call_args
    assert args[0][0] == "scrape.fetch_page"
    assert args[1]["queue"] == "fetching_queue"
