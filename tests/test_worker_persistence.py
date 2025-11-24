import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from services.api import database as db_mod
from services.api import db_utils
from services.ai_worker.tasks import process_request_full

# Use a separate test DB for this module
TEST_DB_URL = "sqlite:///./test_worker_persistence.db"

def setup_module(module):
    if os.path.exists("test_worker_persistence.db"):
        try:
            os.remove("test_worker_persistence.db")
        except:
            pass
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    db_mod.engine.dispose()
    db_mod.engine = engine
    db_mod.SessionLocal.configure(bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)

def teardown_module(module):
    try:
        db_mod.Base.metadata.drop_all(bind=db_mod.engine)
        if os.path.exists("test_worker_persistence.db"):
            os.remove("test_worker_persistence.db")
    except Exception:
        pass

@patch("services.ai_worker.tasks.celery_app.send_task")
@patch("services.ai_worker.tasks.extract_intent")
def test_process_request_full_persistence(mock_extract_intent, mock_send_task):
    # Setup mocks
    mock_extract_intent.return_value = {"target": "jobs", "keywords": ["python"]}
    
    # Create initial task
    db = db_mod.SessionLocal()
    t = db_utils.create_scraping_task(db, "task_p1", "http://example.com", "find jobs")
    db.commit()
    db.close()
    
    # Run function
    result = process_request_full("task_p1", "http://example.com", "find jobs")
    
    assert result["status"] == "IN_PROGRESS"
    assert "Delegated" in result["message"]
    
    # Verify DB update
    db = db_mod.SessionLocal()
    task = db_utils.get_scraping_task(db, "task_p1")
    assert task.status == "STARTED" # process_request_full sets it to STARTED before delegating
    db.close()
    
    # Verify delegation
    mock_send_task.assert_called_once()
    args = mock_send_task.call_args
    assert args[0][0] == "scrape.fetch_page"
    assert args[1]["queue"] == "fetching_queue"
