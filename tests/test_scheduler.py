
import pytest
from datetime import datetime, timezone, timedelta
from services.scheduler.tasks import check_due_jobs
import shared.database as db_utils
from shared.database import ScheduledJob
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database import Base, get_db
from services.api.main import app
from unittest.mock import MagicMock, patch

# Use the same DB setup as conftest, but specialized for this test file logic if needed
# Or reuse conftest fixtures if possible. Since this tests celery task which uses SessionLocal,
# we might need to patch SessionLocal in tasks.py

@patch('services.scheduler.tasks.SessionLocal')
@patch('services.scheduler.tasks.celery_app.send_task')
def test_scheduler_check_due_jobs(mock_send_task, mock_session_cls):
    # Mock DB session
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    
    # Create a due job
    now = datetime.now(timezone.utc)
    past = now - timedelta(minutes=10)
    
    job = ScheduledJob(
        id=1,
        url="http://example.com",
        prompt="test",
        schedule_cron="*/5 * * * *",
        is_active=True,
        owner_id=1,
        next_run_at=past,
        last_run_at=None
    )
    
    mock_db.query.return_value.filter.return_value.all.return_value = [job]
    
    # Run task
    check_due_jobs()
    
    # Verify task was sent
    mock_send_task.assert_called_once()
    args = mock_send_task.call_args[1]['args']
    assert args[1] == "http://example.com"
    
    # Verify job update (next_run_at should be in future)
    assert job.next_run_at > now
    mock_db.commit.assert_called()
