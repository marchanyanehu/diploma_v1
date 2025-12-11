from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import urlparse

from shared.celery_app import celery_app
from services.api.database import SessionLocal
from services.api import db_utils
from shared.input_sanitization import sanitize_user_input, InputSanitizationError
from .intent_extraction import extract_intent
from shared.llm_client import LLMClient
from . import workflows
from . import utils

logger = logging.getLogger(__name__)

@celery_app.task(name="scrape.process_request_full")
def process_request_full(task_id: str, url: str, prompt: str) -> Dict[str, Any]:
    """Entry point: Analyze intent and decide next steps."""
    logger.info("ai.process_request_full.received", extra={"task_id": task_id, "url": url})
    
    db = SessionLocal()
    try:
        # Sanitize input (defense in depth)
        try:
            prompt = sanitize_user_input(prompt)
        except InputSanitizationError as e:
            logger.warning(f"Task {task_id} blocked due to prompt injection: {e}")
            # Ensure task exists so we can mark it as failed
            task = db_utils.get_scraping_task(db, task_id)
            if not task:
                try:
                    # Create as FAILED immediately
                    db_utils.create_scraping_task(db, task_id=task_id, url=url, user_prompt=prompt, status="FAILED")
                except Exception:
                    pass
            else:
                db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message=str(e))
            return {"status": "failed", "error": str(e)}

        task = db_utils.get_scraping_task(db, task_id)
        if not task:
            try:
                task = db_utils.create_scraping_task(db, task_id=task_id, url=url, user_prompt=prompt, status="PENDING")
            except Exception:
                pass

        db_utils.update_task_status(db, task_id=task_id, status="STARTED")

        llm = LLMClient.from_env()
        utils.log_event(task_id, "phase_start", phase="intent_extraction")
        intent = extract_intent(prompt, llm=llm)
        utils.log_event(task_id, "intent_extracted", target=intent.get("target"), keywords=intent.get("keywords"))
        
        celery_app.send_task(
            "scrape.fetch_page",
            args=[task_id, url, intent],
            queue="fetching_queue"
        )
        logger.info("ai.process_request_full.delegated_fetch", extra={"task_id": task_id})
        
        return {"task_id": task_id, "status": "IN_PROGRESS", "message": "Delegated to headless worker"}

    except Exception as exc:
        logger.exception("ai.process_request_full.failed", extra={"task_id": task_id, "error": str(exc)})
        db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message=str(exc))
        return {"task_id": task_id, "status": "FAILED", "error": str(exc)}
    finally:
        db.close()

@celery_app.task(name="scrape.process_content")
def process_content(task_id: str, url: str, intent: Dict, inner_text: str, html_content: str, network: List, duration: int, started_iso: str, completed_iso: str):
    """Process fetched content: Universal Regex Pipeline for any content type."""
    logger.info("ai.process_content.received", extra={"task_id": task_id})
    db = SessionLocal()
    try:
        started = datetime.fromisoformat(started_iso)
        completed = datetime.fromisoformat(completed_iso)

        # Persist sources (including html_content for normalized schema)
        try:
            db_utils.update_task_sources(db, task_id, page_content=inner_text[:200000],
                                         html_content=html_content[:200000] if html_content else None,
                                         network_requests=network, intent=intent, started_at=started)
        except Exception as e:
            logger.warning(f"Failed to persist sources: {e}")

        llm = LLMClient.from_env()
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        # Use full URL as pattern for precise matching
        url_pattern = url
        
        # Prepare content
        text_content = inner_text
        search_content = html_content if html_content and len(html_content) > len(inner_text) else inner_text
        
        # Determine extraction mode
        keywords = intent.get("keywords", [])
        is_multi_field = len(keywords) > 1
        schema_fields = intent.get("schema_fields", [])
        
        extracted_data = []
        used_parser = None
        used_cached = False
        
        # Determine fields to extract (schema_fields or keywords)
        extract_fields = schema_fields if schema_fields else keywords
        
        # 1. Try cache first (field-based caching for semantic content)
        if extract_fields:
            cache_result = workflows.check_cached_parser(
                db, domain, extract_fields, inner_text, 
                source_type="SEMANTIC", min_matches=1, url_pattern=url_pattern
            )
            if cache_result["matches"]:
                extracted_data = cache_result["matches"]
                used_parser = cache_result["used_parser"]
                used_cached = True
                utils.log_event(task_id, "cache_hit", count=len(extracted_data), fields=extract_fields)
        
        # 2. Try direct LLM extraction (simple and effective)
        if not extracted_data:
            if schema_fields:
                # Schema-based extraction with regex caching
                utils.log_event(task_id, "schema_extraction", fields=schema_fields)
                extracted_data = workflows.run_schema_extraction(
                    task_id, url, schema_fields, inner_text, html_content, llm,
                    db=db, domain=domain, url_pattern=url_pattern
                )
            else:
                # Field-based extraction
                utils.log_event(task_id, "field_extraction", fields=keywords)
                extracted_data = workflows.run_field_extraction(
                    task_id, url, keywords, inner_text, html_content, llm, db, domain, url_pattern
                )

        # Persist Results
        if extracted_data:
            db_utils.persist_extraction_result(
                db, task_id, extracted_data=extracted_data, total_matches=len(extracted_data),
                used_parser=used_parser, processing_time_seconds=duration,
                started_at=started, completed_at=completed, used_cached_parser=used_cached
            )
            utils.log_event(task_id, "success", match_count=len(extracted_data))
        else:
            db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message="No data found")
            utils.log_event(task_id, "failed_no_data")

    except Exception as exc:
        logger.exception("ai.process_content.failed")
        db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message=str(exc))
    finally:
        db.close()
