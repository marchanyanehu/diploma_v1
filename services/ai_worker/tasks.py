
from __future__ import annotations

import os
import logging
import json as _json
from typing import Any, Dict, List, Optional, cast
from datetime import datetime, timezone
from urllib.parse import urlparse

from shared.celery_app import celery_app
from services.api.database import SessionLocal
from services.api import db_utils
from shared.intent_extraction import extract_intent
from shared.example_finder import find_target_examples
from shared.snippet_extractor import extract_snippet_around_example
from shared import regex_generation
from shared.llm_client import LLMClient
from shared import metrics

logger = logging.getLogger(__name__)

def _decompose_stored_regex(stored: str) -> tuple[str, str]:
    import re as _re
    m = _re.match(r"\(\?([ims]+):(.*)\)$", stored)
    if m:
        return m.group(2), m.group(1)
    return stored, ""

def _apply_regex_matches(pattern: str, flags: str, source: str) -> list[str]:
    import re
    re_flags = 0
    if 'i' in flags: re_flags |= re.IGNORECASE
    if 'm' in flags: re_flags |= re.MULTILINE
    if 's' in flags: re_flags |= re.DOTALL
    try:
        rx = re.compile(pattern, re_flags)
    except Exception:
        return []
    out: list[str] = []
    for m in rx.finditer(source):
        if m.lastindex and m.lastindex >= 1:
            out.append(m.group(1))
        else:
            out.append(m.group(0))
    return out

def _log_event(task_id: str, event: str, **fields) -> None:
    payload = {"trace_id": task_id, "event": event, **fields}
    try:
        logger.info(_json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.info("%s %s", event, fields)

def _find_candidates_in_html(html: str, examples: List[str]) -> List[Dict[str, Any]]:
    """Find unique snippets in HTML that contain the examples."""
    candidates = []
    seen_snippets = set()
    
    # Simple approach: Find each example, take a snippet (e.g. 500 chars)
    # Better: Navigate DOM (expensive without soup).
    # We'll use string slicing for speed as per 'Optimized' plan (minimize tokens).
    
    for ex in examples:
        if not ex or len(ex) < 3: continue
        start = 0
        while True:
            idx = html.find(ex, start)
            if idx == -1:
                break
            
            # Extract snippet
            s_start = max(0, idx - 200)
            s_end = min(len(html), idx + len(ex) + 200)
            snippet = html[s_start:s_end]
            
            if snippet not in seen_snippets:
                candidates.append({
                    "example_match": ex,
                    "snippet": snippet,
                    "offset": idx
                })
                seen_snippets.add(snippet)
            
            start = idx + 1
            if len(candidates) > 10: # Cap candidates
                break
        if len(candidates) > 20: break
            
    return candidates

def _disambiguate_candidate(candidates: List[Dict], intent: Dict, llm: LLMClient) -> Dict[str, Any]:
    """Ask LLM which candidate snippet looks like the best source."""
    if not candidates:
        return {}
    
    # Prepare candidates for LLM (truncate snippets)
    options = []
    for i, c in enumerate(candidates):
        options.append(f"Option {i}: ...{c['snippet']}...")
    
    prompt = (
        f"TARGET: {intent.get('target')}\n"
        f"KEYWORDS: {intent.get('keywords')}\n"
        f"We found these text fragments in the HTML. Which one seems to be part of the main list/data area we want to extract?\n"
        f"CANDIDATES:\n" + "\n".join(options[:5]) + "\n\n" # Limit to 5 to save tokens
        "Return JSON: {'best_option_index': int, 'reason': str}"
    )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = _json.loads(resp)
        idx = data.get("best_option_index")
        if idx is not None and 0 <= idx < len(candidates):
            return candidates[idx]
    except Exception:
        pass
    
    return candidates[0] # Fallback

@celery_app.task(name="scrape.process_request_full")
def process_request_full(task_id: str, url: str, prompt: str) -> Dict[str, Any]:
    """Entry point: Analyze intent and decide next steps."""
    logger.info("ai.process_request_full.received", extra={"task_id": task_id, "url": url})
    
    db = SessionLocal()
    try:
        # Ensure task exists
        task = db_utils.get_scraping_task(db, task_id)
        if not task:
            try:
                task = db_utils.create_scraping_task(db, task_id=task_id, url=url, user_prompt=prompt, status="PENDING")
            except Exception:
                pass

        db_utils.update_task_status(db, task_id=task_id, status="STARTED")

        # 1. Extract Intent
        llm = LLMClient.from_env()
        _log_event(task_id, "phase_start", phase="intent_extraction")
        intent = extract_intent(prompt, llm=llm)
        _log_event(task_id, "intent_extracted", target=intent.get("target"), keywords=intent.get("keywords"))

        # 2. Check Cache (Quick Reuse)
        domain = urlparse(url).netloc
        keywords = intent.get('keywords', [])
        parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
        
        # Delegate fetch to headless worker
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
    """Process fetched content: Optimized AI Pipeline."""
    logger.info("ai.process_content.received", extra={"task_id": task_id})
    db = SessionLocal()
    try:
        started = datetime.fromisoformat(started_iso)
        completed = datetime.fromisoformat(completed_iso)

        # Persist raw sources
        try:
            db_utils.update_task_sources(
                db,
                task_id,
                page_content=inner_text[:200000], # Visible text is better for reading
                network_requests=network,
                intent=intent,
                started_at=started,
            )
        except Exception as e:
            logger.warning(f"Failed to persist sources: {e}")

        llm = LLMClient.from_env()
        domain = urlparse(url).netloc
        keywords = intent.get("keywords", [])
        
        # Reuse Check
        parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
        used_parser = None
        reuse_matches = []
        used_cached = False
        
        search_content = html_content if len(html_content) < 1000000 else html_content[:1000000] 
        # Truncate massive HTML for safety
        
        for p in parsers:
            patt, fl = _decompose_stored_regex(cast(str, p.generated_regex))
            # Check if pattern matches
            matches = _apply_regex_matches(patt, fl, search_content)
            if matches:
                used_parser = p
                reuse_matches = matches
                used_cached = True
                break
        
        extracted_data = []
        
        if reuse_matches:
            extracted_data = [{"text": m, "source": "cached_regex", "confidence": 1.0} for m in reuse_matches]
        else:
            # OPTIMIZED PIPELINE START
            
            # Step 1: Find Examples using Inner Text (Visible)
            # This saves tokens compared to sending HTML
            _log_event(task_id, "step_1_find_examples")
            examples_found = find_target_examples(inner_text, keywords=keywords, target=intent.get("target"), max_examples=5)
            example_texts = [e["text"] for e in examples_found]
            
            if not example_texts:
                # Fallback: use keywords as examples
                example_texts = keywords[:3]
            
            # Step 2: Find Candidates in HTML (Structure)
            _log_event(task_id, "step_2_find_candidates", example_count=len(example_texts))
            candidates = _find_candidates_in_html(search_content, example_texts)
            
            # Step 3 & 4: Disambiguate
            best_snippet = ""
            if candidates:
                _log_event(task_id, "step_3_disambiguate", candidate_count=len(candidates))
                best = _disambiguate_candidate(candidates, intent, llm)
                best_snippet = best.get("snippet", "")
            
            if not best_snippet:
                # Fallback: extract snippet using legacy logic on HTML
                snip = extract_snippet_around_example(search_content, example_texts[0] if example_texts else "", max_chars=2000)
                best_snippet = cast(str, snip.get("snippet", ""))
            
            # Step 5: Generate Regex on Snippet
            _log_event(task_id, "step_5_generate_regex")
            gen = regex_generation.iterative_regex_generation(
                source=search_content, # We pass full (truncated) source for validation, but snippet for generation prompt
                examples=example_texts,
                target_desc=intent.get("target") or "target data",
                llm=llm,
                max_iterations=2,
                snippet=best_snippet # THIS IS THE KEY: Only passing snippet to LLM prompt
            )
            
            if gen.get("success"):
                pattern = gen.get("final_pattern")
                flags = gen.get("final_flags")
                matches = _apply_regex_matches(pattern, flags, search_content)
                if matches:
                    extracted_data = [{"text": m, "source": "generated_regex", "confidence": 0.9} for m in matches]
                    # Cache it
                    db_utils.record_new_parser(
                        db,
                        task_id=task_id,
                        url=url,
                        intent=intent,
                        pattern=pattern,
                        flags=flags,
                        matches_count=len(matches),
                        source_type="HTML",
                        sample_input=best_snippet,
                        sample_output=[{"text": m} for m in matches[:5]]
                    )

        # Persist Results
        if extracted_data:
            db_utils.persist_extraction_result(
                db, task_id, 
                extracted_data=extracted_data, 
                total_matches=len(extracted_data),
                used_parser=used_parser,
                processing_time_seconds=duration,
                started_at=started,
                completed_at=completed,
                used_cached_parser=used_cached
            )
            _log_event(task_id, "success", match_count=len(extracted_data))
        else:
            db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message="No data found")
            _log_event(task_id, "failed_no_data")

    except Exception as exc:
        logger.exception("ai.process_content.failed")
        db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message=str(exc))
    finally:
        db.close()
