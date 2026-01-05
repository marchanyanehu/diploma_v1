from __future__ import annotations

import logging
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import urlparse

from celery import current_task
from shared.celery_app import celery_app
from shared.database import SessionLocal
import shared.database as db_utils
from shared.correlation import bind_from_headers, get_correlation_id
from shared.logging_utils import configure_logging
from .input_sanitization import sanitize_user_input, InputSanitizationError
from .intent_extraction import extract_intent
from .llm_client import LLMClient
from .prompts import FIELD_NORMALIZATION_SYSTEM_PROMPT, FIELD_NORMALIZATION_USER_TEMPLATE
from . import workflows
from . import utils

configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)


def _bind_task_correlation_id() -> str:
    try:
        headers = getattr(current_task.request, "headers", None)
    except Exception:
        headers = None
    return bind_from_headers(headers)

@celery_app.task(name="scrape.process_request_full")
def process_request_full(task_id: str, url: str, prompt: str) -> Dict[str, Any]:
    """Entry point: Analyze intent and decide next steps."""
    cid = _bind_task_correlation_id()
    logger.info("ai.process_request_full.received", extra={"task_id": task_id, "url": url, "correlation_id": cid})
    
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

        # Mark task as actively processing; API treats IN_PROGRESS as running
        db_utils.update_task_status(db, task_id=task_id, status="IN_PROGRESS")

        llm = LLMClient.from_env()
        utils.log_event(task_id, "phase_start", phase="intent_extraction")
        intent = extract_intent(prompt, llm=llm)
        utils.log_event(task_id, "intent_extracted", target=intent.get("target"), keywords=intent.get("keywords"))
        
        celery_app.send_task(
            "scrape.fetch_page",
            args=[task_id, url, intent],
            queue="fetching_queue",
            headers={"correlation_id": get_correlation_id()},
        )
        logger.info("ai.process_request_full.delegated_fetch", extra={"task_id": task_id, "correlation_id": cid})
        
        return {"task_id": task_id, "status": "IN_PROGRESS", "message": "Delegated to headless worker"}

    except Exception as exc:
        logger.exception("ai.process_request_full.failed", extra={"task_id": task_id, "error": str(exc)})
        db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message=str(exc))
        return {"task_id": task_id, "status": "FAILED", "error": str(exc)}
    finally:
        db.close()

def _normalize_fields(fields: List[str], llm: Optional[LLMClient] = None) -> List[str]:
    """Normalize field names to improve LLM consistency using AI when available.
    
    Avoids hardcoding field-specific heuristics (like 'price' or 'image').
    """
    if not fields:
        return []
        
    # Basic string cleaning (always safe and non-heuristic)
    cleaned = []
    for f in fields:
        if not f: continue
        low = f.strip().lower().replace("-", " ").replace(".", " ")
        cleaned.append("_".join(low.split()))
    
    # If llm is provided, use it for intelligent normalization (avoiding hardcoding)
    if llm:
        try:
            messages = [
                {"role": "system", "content": FIELD_NORMALIZATION_SYSTEM_PROMPT},
                {"role": "user", "content": FIELD_NORMALIZATION_USER_TEMPLATE.format(fields=", ".join(cleaned))}
            ]
            raw = llm.chat(messages, temperature=0.1, extra_params={"response_format": {"type": "json_object"}})
            data = json.loads(raw)
            norm = data.get("normalized_fields", [])
            if isinstance(norm, list) and norm:
                return list(dict.fromkeys(str(n) for n in norm if n))
        except Exception as e:
            logger.warning(f"AI field normalization failed: {e}")
            
    return list(dict.fromkeys(cleaned))  # fallback to basic cleaned list


@celery_app.task(name="scrape.process_content")
def process_content(task_id: str, url: str, intent: Dict, inner_text: str, html_content: str, network: List, duration: int, started_iso: str, completed_iso: str):
    """Process fetched content: Universal Regex Pipeline for any content type."""
    cid = _bind_task_correlation_id()
    logger.info("ai.process_content.received", extra={"task_id": task_id, "correlation_id": cid})
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
        
        # Determine extraction mode
        keywords = _normalize_fields(intent.get("keywords", []), llm=llm)
        schema_fields = _normalize_fields(intent.get("schema_fields", []), llm=llm)
        
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
                    task_id, keywords, inner_text, html_content, llm, db, domain, url_pattern
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
