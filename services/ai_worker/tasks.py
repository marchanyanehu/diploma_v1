
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

def _find_candidates_in_content(content: str, examples: List[str]) -> List[Dict[str, Any]]:
    """Find unique snippets in content that contain the examples."""
    candidates = []
    seen_snippets = set()
    
    for ex in examples:
        if not ex or len(ex) < 3: continue
        start = 0
        while True:
            idx = content.find(ex, start)
            if idx == -1:
                break
            
            # Extract snippet with context
            s_start = max(0, idx - 300)
            s_end = min(len(content), idx + len(ex) + 300)
            snippet = content[s_start:s_end]
            
            if snippet not in seen_snippets:
                candidates.append({
                    "example_match": ex,
                    "snippet": snippet,
                    "offset": idx
                })
                seen_snippets.add(snippet)
            
            start = idx + 1
            if len(candidates) > 10:
                break
        if len(candidates) > 20: break
            
    return candidates

def _disambiguate_candidate(candidates: List[Dict], intent: Dict, llm: LLMClient) -> Dict[str, Any]:
    """Ask LLM which candidate snippet looks like the best source."""
    if not candidates:
        return {}
    
    options = []
    for i, c in enumerate(candidates):
        options.append(f"Option {i}: ...{c['snippet']}...")
    
    prompt = (
        f"TARGET: {intent.get('target')}\n"
        f"KEYWORDS: {intent.get('keywords')}\n"
        f"We found these text fragments. Which one seems to be part of the main data area we want to extract?\n"
        f"CANDIDATES:\n" + "\n".join(options[:5]) + "\n\n"
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
    
    return candidates[0]

def _find_examples_via_llm(text: str, target: str, llm: LLMClient, find_titles_for_urls: bool = False) -> List[str]:
    """Use LLM to find concrete examples of target data in content.
    
    Args:
        text: The content to search in (usually inner_text)
        target: The target data type (e.g. "job links", "prices")
        llm: LLM client
        find_titles_for_urls: If True, find item titles (e.g. job titles) instead of URLs.
                              Used when we need to find text anchors to locate URLs in HTML.
    """
    snippet = text[:32768]
    
    # Detect if target is about URLs/links
    target_lower = target.lower()
    is_url_target = any(word in target_lower for word in ['link', 'url', 'href', 'uri'])
    
    if find_titles_for_urls or is_url_target:
        # For URL targets on visible text: find item TITLES (not URLs, which aren't in innerText).
        # E.g. for "job links", find job titles like "VP Quality", "Software Engineer"
        # These titles can then be searched in HTML to find the surrounding <a href="...">
        item_type = "job" if "job" in target_lower else "item"
        prompt = (
            f"I need to extract '{target}' from the page. The visible text is below.\n"
            f"Find 3-5 distinct {item_type} TITLES or NAMES that appear in this text.\n"
            f"These should be specific item names, NOT generic phrases like 'Apply' or 'Jobs powered by'.\n"
            f"Look for things like: job titles, product names, article headlines, etc.\n\n"
            f"Return ONLY a JSON object: {{\"examples\": [\"Item Title 1\", \"Item Title 2\"]}}\n"
            f"If none found, return {{\"examples\": []}}.\n\n"
            f"CONTENT:\n{snippet}"
        )
    else:
        prompt = (
            f"I need to extract '{target}' from the content below.\n"
            f"Identify 3-5 distinct, concrete examples of '{target}' found in the text.\n"
            f"Return the EXACT substrings as they appear in the content.\n"
            f"Return ONLY a JSON object: {{\"examples\": [\"example1\", \"example2\"]}}\n"
            f"If none found, return {{\"examples\": []}}.\n\n"
            f"CONTENT:\n{snippet}"
        )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = _json.loads(resp)
        
        examples = []
        if isinstance(data, list):
            examples = [str(x) for x in data if x]
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    examples = [str(x) for x in v if x]
                    break
        
        logger.info(f"LLM found {len(examples)} examples for '{target}': {examples[:3]}")
        return examples
        
    except Exception as e:
        logger.warning(f"Example finding via LLM failed: {e}")
        return []


@celery_app.task(name="scrape.process_request_full")
def process_request_full(task_id: str, url: str, prompt: str) -> Dict[str, Any]:
    """Entry point: Analyze intent and decide next steps."""
    logger.info("ai.process_request_full.received", extra={"task_id": task_id, "url": url})
    
    db = SessionLocal()
    try:
        task = db_utils.get_scraping_task(db, task_id)
        if not task:
            try:
                task = db_utils.create_scraping_task(db, task_id=task_id, url=url, user_prompt=prompt, status="PENDING")
            except Exception:
                pass

        db_utils.update_task_status(db, task_id=task_id, status="STARTED")

        llm = LLMClient.from_env()
        _log_event(task_id, "phase_start", phase="intent_extraction")
        intent = extract_intent(prompt, llm=llm)
        _log_event(task_id, "intent_extracted", target=intent.get("target"), keywords=intent.get("keywords"))

        domain = urlparse(url).netloc
        keywords = intent.get('keywords', [])
        
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

        try:
            db_utils.update_task_sources(
                db,
                task_id,
                page_content=inner_text[:200000],
                network_requests=network,
                intent=intent,
                started_at=started,
            )
        except Exception as e:
            logger.warning(f"Failed to persist sources: {e}")

        llm = LLMClient.from_env()
        domain = urlparse(url).netloc
        keywords = intent.get("keywords", [])
        
        # Determine if target is URL-based (links, urls, hrefs)
        target = intent.get("target", "") or ""
        target_lower = target.lower()
        is_url_target = any(word in target_lower for word in ['link', 'url', 'href', 'uri'])
        
        # Prepare content sources:
        # - text_content: for finding examples (visible text like job titles)
        # - html_search_content: for regex matching (contains hrefs for URL targets)
        text_content = inner_text if len(inner_text) < 1000000 else inner_text[:1000000]
        html_search_content = html_content if len(html_content) < 1000000 else html_content[:1000000] if html_content else text_content
        
        # For URL targets, we'll search in HTML; for text targets, in inner_text
        search_content = html_search_content if is_url_target else text_content
        
        # Check for cached parser
        parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
        used_parser = None
        reuse_matches = []
        used_cached = False
        
        for p in parsers:
            patt, fl = _decompose_stored_regex(cast(str, p.generated_regex))
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
            # UNIVERSAL REGEX PIPELINE
            
            # Step 1: Find Examples from inner_text (visible text like job titles)
            # For URL targets, use LLM directly since keyword matching won't find URLs in text
            _log_event(task_id, "step_1_find_examples", is_url_target=is_url_target)
            example_texts = []
            
            if is_url_target:
                # For URL targets, keyword-based finder won't work well (e.g. "VP Quality" 
                # doesn't contain "job"). Use LLM to find relevant text like job titles.
                _log_event(task_id, "step_1_llm_for_url_target")
                example_texts = _find_examples_via_llm(text_content, intent.get("target", "") or "target data", llm)
            else:
                examples_found = find_target_examples(text_content, keywords=keywords, target=intent.get("target"), max_examples=5)
                example_texts = [e["text"] for e in examples_found]
            
            if not example_texts:
                _log_event(task_id, "step_1_fallback_llm_examples")
                example_texts = _find_examples_via_llm(text_content, intent.get("target", "") or "target data", llm)

            if not example_texts:
                example_texts = keywords[:3]
            
            _log_event(task_id, "examples_found", count=len(example_texts), samples=example_texts[:3])
            
            # Step 2: Find candidate snippets containing examples
            # For URL targets: search in HTML to find the surrounding markup with hrefs
            # For text targets: search in inner_text
            _log_event(task_id, "step_2_find_candidates", example_count=len(example_texts), using_html=is_url_target)
            candidates = _find_candidates_in_content(search_content, example_texts)
            
            # Step 3: Disambiguate best snippet
            best_snippet = ""
            if candidates:
                _log_event(task_id, "step_3_disambiguate", candidate_count=len(candidates))
                best = _disambiguate_candidate(candidates, intent, llm)
                best_snippet = best.get("snippet", "")
            
            if not best_snippet:
                snip = extract_snippet_around_example(search_content, example_texts[0] if example_texts else "", max_chars=4000)
                best_snippet = cast(str, snip.get("snippet", ""))
            
            # Step 4: Generate Regex using enhanced prompt
            _log_event(task_id, "step_4_generate_regex")
            
            # Use a larger snippet for regex generation to ensure examples are visible
            snippet_to_use = best_snippet
            if len(search_content) > 10000 and len(best_snippet) < 4000:
                missing_count = sum(1 for ex in example_texts if ex not in best_snippet)
                if missing_count > 0:
                    # Include more content to ensure examples are present
                    snippet_to_use = search_content[:32000]

            # For URL targets: extract actual URLs from HTML near the text anchors
            # The regex validation needs URL examples to match, not text anchors
            regex_examples = example_texts
            if is_url_target and best_snippet:
                import re as _re
                # Find URLs in the snippet (from href attributes)
                url_pattern = r'href=["\']?(https?://[^"\'>\s]+)'
                found_urls = _re.findall(url_pattern, best_snippet)
                if found_urls:
                    # Use found URLs as examples for regex generation
                    regex_examples = list(dict.fromkeys(found_urls))[:5]  # dedupe, limit to 5
                    _log_event(task_id, "extracted_url_examples", urls=regex_examples[:3])
                regex_target_desc = f"{target} - extract href URL values from <a> tags"
            else:
                regex_target_desc = intent.get("target") or "target data"

            gen = regex_generation.iterative_regex_generation(
                source=search_content,
                examples=regex_examples,
                target_desc=regex_target_desc,
                llm=llm,
                max_iterations=3,
                snippet=snippet_to_use 
            )
            
            if gen.get("success"):
                pattern = gen.get("final_pattern")
                flags = gen.get("final_flags", "s")  # Default to DOTALL
                matches = _apply_regex_matches(pattern, flags, search_content)
                if matches:
                    extracted_data = [{"text": m, "source": "generated_regex", "confidence": 0.9} for m in matches]
                    db_utils.record_new_parser(
                        db,
                        task_id=task_id,
                        url=url,
                        intent=intent,
                        pattern=pattern,
                        flags=flags,
                        matches_count=len(matches),
                        source_type="CONTENT",
                        sample_input=best_snippet[:2000],
                        sample_output=[{"text": m} for m in matches[:5]]
                    )
                    _log_event(task_id, "regex_success", pattern=pattern[:100], match_count=len(matches))
            else:
                _log_event(task_id, "regex_generation_failed", error=gen.get("error"), attempts=len(gen.get("attempts", [])))

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
