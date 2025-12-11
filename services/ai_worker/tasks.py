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
        domain = urlparse(url).netloc
        
        # Prepare content
        text_content = inner_text
        search_content = html_content if html_content and len(html_content) > len(inner_text) else inner_text
        
        # Determine extraction mode
        keywords = intent.get("keywords", [])
        is_multi_field = len(keywords) > 1
        is_attribute_target = intent.get("is_attribute", False)
        schema_fields = intent.get("schema_fields", [])
        
        extracted_data = []
        used_parser = None
        used_cached = False
        
        # 1. Check Cache
        cache_result = workflows.check_cached_parser(db, domain, keywords, search_content)
        if cache_result["matches"]:
            # If schema extraction is requested, ensure we don't use a CONTENT parser
            parser = cache_result["used_parser"]
            if schema_fields and parser and parser.source_type != "SCHEMA":
                utils.log_event(task_id, "cache_hit_ignored_type_mismatch", expected="SCHEMA", found=parser.source_type)
            else:
                extracted_data = [{"text": m, "source": "cached_regex", "confidence": 1.0} for m in cache_result["matches"]]
                used_parser = parser
                used_cached = True
                if used_parser:
                    try:
                        db_utils.update_parser_usage(db, used_parser.id)
                    except Exception as e:
                        utils.log_event(task_id, "update_parser_usage_failed", error=str(e))
        
        # 2. Schema Extraction (if requested and no cache hit)
        if not extracted_data and schema_fields:
            utils.log_event(task_id, "using_schema_extraction", fields=schema_fields)
            extracted_data, schema_used_cache = workflows.run_schema_extraction_with_cache(
                task_id, url, schema_fields, inner_text, html_content, llm, db, domain
            )
            if schema_used_cache:
                used_cached = True
            if extracted_data:
                utils.log_event(task_id, "schema_extraction_complete", count=len(extracted_data))
                
                # Quality check: for multi-field extraction (like products), 
                # if we only got 1-2 records, it's likely wrong (e.g., page title instead of products)
                if is_multi_field and len(extracted_data) <= 2:
                    utils.log_event(task_id, "schema_extraction_low_count", 
                                  count=len(extracted_data),
                                  reason="Too few records for product listing, will try alternatives")
                    extracted_data = []  # Reset to try other methods

        # 3. NEW: Try simplified extraction strategies first (combined regex or direct LLM)
        # These avoid the complex position-based grouping logic
        if not extracted_data and is_multi_field:
            from . import extraction_strategies
            
            field_keywords = keywords
            utils.log_event(task_id, "trying_simplified_extraction", fields=field_keywords)
            
            strategy_result = extraction_strategies.unified_extract(
                html=html_content,
                fields=field_keywords,
                llm=llm,
                task_id=task_id
            )
            
            if strategy_result.get("success") and strategy_result.get("records"):
                utils.log_event(task_id, "simplified_extraction_success", 
                              strategy=strategy_result.get("strategy_used"),
                              count=len(strategy_result["records"]))
                # Convert to expected format
                extracted_data = []
                for record in strategy_result["records"]:
                    filtered_record = {k: v for k, v in record.items() if v is not None}
                    if filtered_record:
                        text_repr = " | ".join(f"{k}: {v}" for k, v in filtered_record.items())
                        extracted_data.append({
                            "text": text_repr,
                            "fields": record,
                            "source": f"strategy_{strategy_result.get('strategy_used', 'unknown')}",
                            "confidence": 0.85
                        })
            elif strategy_result.get("quality_issue"):
                utils.log_event(task_id, "simplified_extraction_quality_fail", 
                              error=strategy_result.get("error"),
                              match_count=strategy_result.get("match_count"))
                # Will fallback to per-field extraction below
            else:
                utils.log_event(task_id, "simplified_extraction_failed", 
                              error=strategy_result.get("error"))

        # 4. Universal Extraction Pipeline (fallback to original per-field approach)
        if not extracted_data:
            utils.log_event(task_id, "step_1_inner_text_ready", length=len(text_content))
            
            # Step 2: Find matching text
            matched_texts = workflows.step2_find_matching_text(
                task_id, text_content, intent, is_multi_field, is_attribute_target, keywords, llm
            )
            utils.log_event(task_id, "step_2_complete", count=len(matched_texts), samples=matched_texts[:3])
            
            if is_attribute_target:
                extracted_data = workflows.run_attribute_extraction(
                    task_id, url, intent, matched_texts, html_content, llm, db
                )
            
            # Use unified field extraction for both single and multi-field
            if not extracted_data:
                utils.log_event(task_id, "field_extraction_start", is_multi_field=is_multi_field)
                
                # For single field, use the target as the field name
                if not is_multi_field:
                    field_keywords = [intent.get("target", "value")]
                else:
                    field_keywords = keywords
                
                extracted_data = workflows.run_multi_field_extraction(
                    task_id=task_id,
                    keywords=field_keywords,
                    example_texts=matched_texts,
                    search_content=search_content,
                    snippet_to_use=search_content[:32000],
                    llm=llm,
                    url=url,
                    db=db,
                    intent=intent
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
