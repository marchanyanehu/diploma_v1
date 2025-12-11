
import logging
from datetime import datetime, timezone
from sqlalchemy import or_
from croniter import croniter
from shared.celery_app import celery_app
from shared.database import SessionLocal, ScheduledJob
import shared.database as db_utils

logger = logging.getLogger(__name__)

@celery_app.task(name="scheduler.check_due_jobs")
def check_due_jobs():
    """
    Periodic task to check for scheduled jobs that need to run.
    """
    logger.info("Checking for due scheduled jobs...")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Find active jobs where next_run_at is null (never ran) or past
        jobs = db.query(ScheduledJob).filter(
            ScheduledJob.is_active == True,
            or_(ScheduledJob.next_run_at == None, ScheduledJob.next_run_at <= now)
        ).all()
        
        for job in jobs:
            logger.info(f"Triggering job {job.id} ({job.url})")
            
            # Calculate next run time
            try:
                iter = croniter(job.schedule_cron, now)
                next_run = iter.get_next(datetime)
                
                # Update job state
                job.last_run_at = now
                job.next_run_at = next_run
                db.commit()
                
                # Trigger the scraping task
                # We simulate a request by calling the process endpoint logic via celery directly
                # or we could create a helper in api/main to reuse.
                # Better: Create a ScrapingTask and enqueue it, similar to api.process_request
                
                task_id = f"scheduled-{job.id}-{int(now.timestamp())}"
                
                db_utils.create_scraping_task(
                    db=db,
                    task_id=task_id,
                    url=str(job.url),
                    user_prompt=job.prompt,
                    status="PENDING",
                    owner_id=job.owner_id
                )
                
                celery_app.send_task(
                    "scrape.process_request_full",
                    args=[task_id, str(job.url), job.prompt],
                    queue="ai_queue"
                )
                
            except Exception as e:
                logger.error(f"Failed to process scheduled job {job.id}: {e}")
                db.rollback()
                continue
                
    finally:
        db.close()
