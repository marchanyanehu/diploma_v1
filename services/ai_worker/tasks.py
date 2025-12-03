
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

def _extract_snippet(content: str, idx: int, example_len: int, context: int = 300) -> str:
    """Extract a snippet from content around a given index."""
    s_start = max(0, idx - context)
    s_end = min(len(content), idx + example_len + context)
    return content[s_start:s_end]


def _filter_values_via_llm(values: List[str], target: str, llm: LLMClient) -> List[str]:
    """Use LLM to filter out noise from extracted attribute values."""
    if not values:
        return []
    
    # Deduplicate
    unique_values = list(dict.fromkeys(values))
    
    # If we have too many values, we might need to batch, but for now let's cap at 100
    # to avoid massive prompts. If > 100, we assume they are mostly correct or we filter top 100.
    # A better approach would be to chunk, but let's start simple.
    chunk = unique_values[:100]
    
    prompt = (
        f"I am extracting '{target}' from a webpage.\n"
        f"I found the following candidate values (e.g. URLs, sources, text).\n"
        f"Please filter out any values that clearly DO NOT match the target '{target}'\n"
        f"(e.g. if looking for job posts, remove image URLs, javascript links, or navigation links).\n"
        f"If looking for images, keep image URLs.\n\n"
        f"CANDIDATES: {chunk}\n\n"
        f"Return ONLY a JSON object: {{\"valid_values\": [\"val1\", \"val2\"]}}\n"
        f"Return ALL valid values from the list."
    )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = _json.loads(resp)
        valid = data.get("valid_values", [])
        
        # If valid is empty but we had inputs, and it's not obvious why, 
        # it might be an LLM error. But we trust the filter for now.
        
        # Restore the rest of the values if we truncated
        if len(unique_values) > 100:
            # We only filtered the first 100. The rest are returned as is (risky) 
            # or we drop them? Let's append them but log warning.
            # Actually, let's just return what we verified + the rest? No, inconsistent.
            # Let's just filter the top 100.
            pass
            
        return [str(v) for v in valid]
    except Exception as e:
        logger.warning(f"LLM filtering failed: {e}")
        return unique_values # Fallback: return original list

def _extract_attribute_from_html_by_text(html_content: str, text_examples: List[str], attribute: str) -> List[str]:
    """Extract specific attribute values from HTML by finding elements that contain the given text examples.
    
    Args:
        html_content: Raw HTML content
        text_examples: List of visible text strings to look for in tags
        attribute: The attribute to extract (e.g., 'href', 'src', 'data-id')
        
    Returns:
        List of unique attribute values found
    """
    import re
    values = []
    seen_values: set = set()
    
    # Normalize attribute name
    attr = attribute.lower()
    
    # Heuristic regex: Find opening tag with the attribute, capture value and some following content
    # This captures: <TAG ... attr="VALUE" ...>...CONTENT...
    # We look for the example text in ...CONTENT...
    
    # Note: This is a simplified regex for HTML parsing. It works well for standard <a> tags
    # and elements where text is immediately inside.
    pattern = re.compile(
        f'<[^>]*\\s+{re.escape(attr)}=["\']([^"\']+)["\'][^>]*>(.*?)</',
        re.IGNORECASE | re.DOTALL
    )
    
    for match in pattern.finditer(html_content):
        val = match.group(1)
        content = match.group(2)
        
        # Strip inner tags from content to get visible text
        clean_text = re.sub(r'<[^>]+>', '', content).strip()
        
        # Check if any example text appears in the content
        for example in text_examples:
            if example and example.lower() in clean_text.lower():
                # Normalize value (basic)
                if val and val not in seen_values:
                    # Basic noise filtering
                    if val.startswith('#') or val.startswith('javascript:'):
                        continue
                        
                    values.append(val)
                    seen_values.add(val)
                break
                
    return values


def _extract_attribute_via_llm(html_content: str, text_examples: List[str], target: str, attribute: str, llm: LLMClient) -> List[str]:
    """Use LLM to extract attributes from HTML when regex approach fails."""
    # Find snippets around the text examples
    snippets = []
    for ex in text_examples[:3]:
        idx = html_content.lower().find(ex.lower())
        if idx != -1:
            snippet = _extract_snippet(html_content, idx, len(ex), context=500)
            snippets.append(snippet)
    
    if not snippets:
        snippets = [html_content[:10000]]
    
    combined_snippets = "\n---\n".join(snippets[:3])[:15000]
    
    prompt = (
        f"I need to extract '{attribute}' attributes related to '{target}'.\n"
        f"The text examples associated with these elements are: {text_examples[:5]}\n"
        f"Find the values of the '{attribute}' attribute for elements matching these text descriptions.\n"
        f"Return ONLY a JSON object: {{\"values\": [\"value1\", \"value2\"]}}\n"
        f"If none found, return {{\"values\": []}}.\n\n"
        f"HTML SNIPPETS:\n{combined_snippets}"
    )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = _json.loads(resp)
        
        values = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    values = [str(u) for u in v if u]
                    break
        
        logger.info(f"LLM extracted {len(values)} {attribute} values for '{target}'")
        return values
        
    except Exception as e:
        logger.warning(f"LLM attribute extraction failed: {e}")
        return []


def _find_text_in_raw_content(raw_content: str, text_examples: List[str], max_candidates: int = 20) -> List[Dict[str, Any]]:
    """Step 3: Find text examples in raw content (no LLM, pure string search).
    
    Args:
        raw_content: The raw content to search in (HTML, JSON, XML, etc.)
        text_examples: Text examples found via LLM from inner_text
        max_candidates: Maximum number of candidate snippets to return
        
    Returns:
        List of candidate dicts with 'example_match', 'snippet', 'offset'
    """
    candidates = []
    seen_snippets: set = set()
    
    for ex in text_examples:
        if not ex or len(ex) < 3:
            continue
        
        start = 0
        while len(candidates) <= max_candidates:
            idx = raw_content.find(ex, start)
            if idx == -1:
                break
            
            snippet = _extract_snippet(raw_content, idx, len(ex))
            if snippet not in seen_snippets:
                candidates.append({"example_match": ex, "snippet": snippet, "offset": idx})
                seen_snippets.add(snippet)
            
            start = idx + 1
            if len(candidates) > 10:
                break
        
        if len(candidates) > max_candidates:
            break
            
    return candidates

def _select_best_candidate_via_llm(candidates: List[Dict], intent: Dict, llm: LLMClient) -> Dict[str, Any]:
    """Step 4: Present candidate snippets to LLM and select the best one.
    
    Args:
        candidates: List of candidate snippets found in raw content
        intent: The extraction intent with target and keywords
        llm: LLM client for decision making
        
    Returns:
        The best candidate dict, or first candidate as fallback
    """
    if not candidates:
        return {}
    
    options = []
    for i, c in enumerate(candidates):
        options.append(f"Option {i}: ...{c['snippet']}...")
    
    prompt = (
        f"TARGET: {intent.get('target')}\n"
        f"KEYWORDS: {intent.get('keywords')}\n"
        f"We found these content snippets containing the target data. Which one is the best source for regex extraction?\n"
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

def _find_matching_text_via_llm(inner_text: str, target: str, llm: LLMClient, is_attribute_target: bool = False) -> List[str]:
    """Step 2: Use LLM to find raw text matching the keyword in inner_text.
    
    Args:
        inner_text: The inner text content (not HTML)
        target: The target data type (e.g. "job links", "prices")
        llm: LLM client
        is_attribute_target: If True, we're looking for text anchors for attribute extraction
        
    Returns:
        List of exact text strings found that match the target
    """
    snippet = inner_text[:32768]
    
    if is_attribute_target:
        # For attribute targets (links, images, etc), we need to find the visible TEXT
        # that anchors the element (e.g. link text, alt text, caption)
        prompt = (
            f"I need to find '{target}' from this page, which are likely in HTML attributes.\n"
            f"Identify 3-5 distinct visible TEXT labels that represent or anchor these items.\n"
            f"For links, this is the clickable text. For images, this might be the caption or alt text.\n"
            f"Return the EXACT text labels as they appear in the content.\n"
            f"Do NOT return URLs/attributes - return the visible text.\n"
            f"Return ONLY a JSON object: {{\"examples\": [\"Label 1\", \"Label 2\"]}}\n"
            f"If none found, return {{\"examples\": []}}.\n\n"
            f"CONTENT:\n{snippet}"
        )
    else:
        prompt = (
            f"I need to extract '{target}' from the text content below.\n"
            f"Identify 3-5 distinct, concrete examples of text that represent '{target}'.\n"
            f"Return the EXACT substrings as they appear in the content.\n"
            f"These should be specific items, NOT generic phrases.\n"
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
        
        logger.info(f"Step 2: LLM found {len(examples)} matching texts for '{target}': {examples[:3]}")
        return examples
        
    except Exception as e:
        logger.warning(f"Step 2 failed - LLM text matching error: {e}")
        return []


def _find_structured_examples_via_llm(text: str, target: str, keywords: List[str], llm: LLMClient) -> List[str]:
    """Find complete structured record examples for multi-field extraction.
    
    For requests like "country names with capital, population, area", this finds
    complete record blocks (e.g., "Zimbabwe\nCapital: Harare\nPopulation: 11651858\nArea: 390580")
    instead of individual lines.
    """
    snippet = text[:32768]
    fields_str = ", ".join(keywords[:5])
    
    prompt = (
        f"I need to extract structured records containing: {fields_str}\n"
        f"Find 2-3 COMPLETE example records from the text below.\n"
        f"Each record should include ALL the fields mentioned above.\n"
        f"Return the EXACT text as it appears, preserving line breaks within each record.\n\n"
        f"Return ONLY a JSON object: {{\"examples\": [\"record1 text\", \"record2 text\"]}}\n"
        f"If no complete records found, return {{\"examples\": []}}.\n\n"
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
        
        logger.info(f"LLM found {len(examples)} structured examples for '{target}': {[e[:50] for e in examples[:2]]}")
        return examples
        
    except Exception as e:
        logger.warning(f"Structured example finding via LLM failed: {e}")
        return []


# ==================== EXTRACTION PIPELINE HELPERS ====================



def _prepare_search_content(inner_text: str, raw_content: str) -> Dict[str, str]:
    """Prepare content sources for extraction.
    
    Args:
        inner_text: Clean text content (for LLM analysis)
        raw_content: Raw content with structure (HTML, JSON, XML, etc.) for regex
    """
    max_content_len = 1000000
    text_content = inner_text[:max_content_len]
    
    # Use raw content for search (has structure needed for regex)
    if raw_content:
        search_content = raw_content[:max_content_len]
    else:
        search_content = text_content
    
    return {
        "text_content": text_content,
        "search_content": search_content,
    }


def _check_cached_parser(db, domain: str, keywords: List[str], search_content: str) -> Dict[str, Any]:
    """Check for and apply cached parser."""
    parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
    
    for p in parsers:
        patt, fl = _decompose_stored_regex(cast(str, p.generated_regex))
        matches = _apply_regex_matches(patt, fl, search_content)
        if matches:
            return {
                "used_parser": p,
                "matches": matches,
                "used_cached": True,
            }
    
    return {"used_parser": None, "matches": [], "used_cached": False}


def _step2_find_matching_text(
    task_id: str, inner_text: str, intent: Dict, 
    is_multi_field: bool, is_attribute_target: bool, keywords: List[str], llm: LLMClient
) -> List[str]:
    """Step 2: Find raw text that matches the keyword via LLM (from inner_text)."""
    target = intent.get("target", "") or "target data"
    matched_texts = []
    
    if is_multi_field:
        _log_event(task_id, "step_2_llm_multi_field_matching")
        matched_texts = _find_structured_examples_via_llm(inner_text, target, keywords, llm)
    else:
        # Use LLM to find matching text in inner_text
        _log_event(task_id, "step_2_llm_text_matching", is_attribute_target=is_attribute_target)
        matched_texts = _find_matching_text_via_llm(inner_text, target, llm, is_attribute_target=is_attribute_target)
    
    # Last resort: use keywords as fallback
    if not matched_texts:
        matched_texts = keywords[:3]
    
    return matched_texts


def _steps3_4_find_and_select_snippet(
    task_id: str, raw_content: str, matched_texts: List[str], 
    intent: Dict, llm: LLMClient
) -> str:
    """Steps 3-4: Find text in raw content (no LLM), then select best candidate via LLM.
    
    Step 3: Find matched_texts in raw content using string search (no LLM)
    Step 4: Provide snippets of candidates to LLM, decide best candidate
    
    Args:
        task_id: Task ID for logging
        raw_content: Raw content to search in (HTML, JSON, XML, etc.)
        matched_texts: Text examples found via LLM from inner_text (step 2)
        intent: Extraction intent
        llm: LLM client for step 4 disambiguation
        
    Returns:
        Best snippet for regex generation
    """
    # Step 3: Find text in raw content (no LLM, pure string search)
    _log_event(task_id, "step_3_find_in_raw_content", text_count=len(matched_texts))
    candidates = _find_text_in_raw_content(raw_content, matched_texts)
    _log_event(task_id, "step_3_candidates_found", candidate_count=len(candidates))
    
    best_snippet = ""
    if candidates:
        # Step 4: Provide snippets to LLM, select best candidate
        _log_event(task_id, "step_4_select_best_candidate", candidate_count=len(candidates))
        best = _select_best_candidate_via_llm(candidates, intent, llm)
        best_snippet = best.get("snippet", "")
    
    # Fallback: extract snippet around first matched text
    if not best_snippet:
        snip = extract_snippet_around_example(raw_content, matched_texts[0] if matched_texts else "", max_chars=4000)
        best_snippet = cast(str, snip.get("snippet", ""))
    
    return best_snippet


def _extract_field_examples(example_texts: List[str], field: str) -> List[str]:
    """Extract field-specific examples from structured examples."""
    field_examples = []
    field_lower = field.lower()
    
    for ex in example_texts:
        for line in ex.split('\n'):
            if field_lower in line.lower():
                if ':' in line:
                    value = line.split(':', 1)[1].strip()
                    if value:
                        field_examples.append(value)
                else:
                    field_examples.append(line.strip())
                break
    
    return list(dict.fromkeys(field_examples))[:3]  # Dedupe and limit


def _run_multi_field_extraction(
    task_id: str, keywords: List[str], example_texts: List[str],
    search_content: str, snippet_to_use: str, llm: LLMClient
) -> List[Dict[str, Any]]:
    """Generate separate regex for each field and combine results."""
    _log_event(task_id, "multi_field_extraction", fields=keywords)
    field_results = {}
    
    for field in keywords:
        field_examples = _extract_field_examples(example_texts, field)
        if not field_examples:
            continue
        
        _log_event(task_id, "field_examples", field=field, examples=field_examples)
        
        gen = regex_generation.iterative_regex_generation(
            source=search_content,
            examples=field_examples,
            target_desc=f"{field} values",
            llm=llm,
            max_iterations=2,
            snippet=snippet_to_use
        )
        
        if gen.get("success"):
            pattern = gen.get("final_pattern")
            flags = gen.get("final_flags", "s")
            matches = _apply_regex_matches(pattern, flags, search_content)
            if matches:
                unique = list(dict.fromkeys(matches))
                field_results[field] = unique
                _log_event(task_id, "field_regex_success", field=field, match_count=len(unique))
    
    # Combine field results into records
    extracted_data = []
    if field_results:
        max_len = max(len(v) for v in field_results.values())
        for i in range(max_len):
            record = {field: values[i] for field, values in field_results.items() if i < len(values)}
            if record:
                text_repr = " | ".join(f"{k}: {v}" for k, v in record.items())
                extracted_data.append({
                    "text": text_repr,
                    "fields": record,
                    "source": "multi_field_regex",
                    "confidence": 0.85
                })
        _log_event(task_id, "multi_field_success", record_count=len(extracted_data))
    
    return extracted_data


def _run_attribute_extraction(
    task_id: str, _url: str, intent: Dict, text_examples: List[str],
    html_content: str, llm: LLMClient, _db
) -> List[Dict[str, Any]]:
    """Extract attributes from HTML using text examples as anchors.
    
    This is a generic extraction for when source_type is 'attribute'.
    We use the text examples (visible text) to find corresponding attribute values.
    """
    target = intent.get("target", "") or "target data"
    attribute = intent.get("target_attribute", "") or "href" # default to href if missing
    
    _log_event(task_id, "attribute_extraction_start", attribute=attribute, text_examples=text_examples[:3])
    
    # First try: Simple regex-based extraction
    values = _extract_attribute_from_html_by_text(html_content, text_examples, attribute)
    _log_event(task_id, "attribute_extraction_regex", found_count=len(values))
    
    # If regex approach didn't find enough, try LLM
    if len(values) < len(text_examples) // 2:
        _log_event(task_id, "attribute_extraction_llm_fallback")
        llm_values = _extract_attribute_via_llm(html_content, text_examples, target, attribute, llm)
        # Merge, avoiding duplicates
        seen = set(values)
        for v in llm_values:
            if v not in seen:
                values.append(v)
                seen.add(v)
    
    extracted_data = []
    if values:
        # Filter values via LLM to remove noise (images, bad links) based on target
        # This avoids hardcoded rules about SVGs etc.
        filtered_values = _filter_values_via_llm(values, target, llm)
        
        unique_values = list(dict.fromkeys(filtered_values))  # Preserve order, dedupe
        extracted_data = [{"text": v, "source": f"{attribute}_extraction", "confidence": 0.95} for v in unique_values]
        _log_event(task_id, "attribute_extraction_success", count=len(unique_values))
    else:
        _log_event(task_id, "attribute_extraction_failed", text_example_count=len(text_examples))
    
    return extracted_data


def _run_single_field_extraction(
    task_id: str, url: str, intent: Dict, example_texts: List[str],
    search_content: str, best_snippet: str, snippet_to_use: str,
    llm: LLMClient, db
) -> List[Dict[str, Any]]:
    """Generate regex for single-field extraction."""
    import re as _re
    
    target = intent.get("target", "") or "target data"

    gen = regex_generation.iterative_regex_generation(
        source=search_content,
        examples=example_texts,
        target_desc=target,
        llm=llm,
        max_iterations=3,
        snippet=snippet_to_use
    )
    
    extracted_data = []
    if gen.get("success"):
        pattern = gen.get("final_pattern")
        flags = gen.get("final_flags", "s")
        matches = _apply_regex_matches(pattern, flags, search_content)
        
        if matches:
            unique_matches = list(dict.fromkeys(matches))  # Dedupe
            
            if unique_matches:
                extracted_data = [{"text": m, "source": "generated_regex", "confidence": 0.9} for m in unique_matches]
                db_utils.record_new_parser(
                    db,
                    task_id=task_id,
                    url=url,
                    intent=intent,
                    pattern=pattern,
                    flags=flags,
                    matches_count=len(unique_matches),
                    source_type="CONTENT",
                    sample_input=best_snippet[:2000],
                    sample_output=[{"text": m} for m in unique_matches[:5]]
                )
                _log_event(task_id, "regex_success", pattern=pattern[:100], match_count=len(unique_matches))
    else:
        _log_event(task_id, "regex_generation_failed", error=gen.get("error"), attempts=len(gen.get("attempts", [])))
    
    return extracted_data


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

        # Persist sources
        try:
            db_utils.update_task_sources(db, task_id, page_content=inner_text[:200000],
                                         network_requests=network, intent=intent, started_at=started)
        except Exception as e:
            logger.warning(f"Failed to persist sources: {e}")

        llm = LLMClient.from_env()
        domain = urlparse(url).netloc
        keywords = intent.get("keywords", [])
        target = intent.get("target", "")
        
        # Detect target type and prepare content
        # We rely on the intent extractor to tell us if this is an attribute extraction
        target_attribute = intent.get("target_attribute")
        is_attribute_target = bool(target_attribute) or intent.get("source_type") == "attribute"
        # Fallback: if source_type is attribute but no attribute specified, default to href (most common)
        if is_attribute_target and not target_attribute:
            target_attribute = "href"
            
        # Also detect multi-field
        is_multi_field = len(keywords) >= 3 and not is_attribute_target
        
        _log_event(task_id, "target_type_detected", is_multi_field=is_multi_field, is_attribute_target=is_attribute_target, target_attribute=target_attribute)
        
        content = _prepare_search_content(inner_text, html_content)
        text_content = content["text_content"]
        search_content = content["search_content"]
        
        # Check for cached parser (skip for attribute targets as they use different approach)
        cache_result = {"used_parser": None, "matches": [], "used_cached": False}
        if not is_attribute_target:
            cache_result = _check_cached_parser(db, domain, keywords, search_content)
        used_parser = cache_result["used_parser"]
        used_cached = cache_result["used_cached"]
        
        extracted_data = []
        
        if cache_result["matches"]:
            extracted_data = [{"text": m, "source": "cached_regex", "confidence": 1.0} for m in cache_result["matches"]]
        else:
            # UNIVERSAL EXTRACTION PIPELINE
            # Flow depends on target type:
            # - Attribute targets (e.g. URLs, SRCs): Find text anchors -> extract attribute
            # - Text targets: Find text examples -> generate regex
            
            # Step 1: Get inner text (already done in content preparation)
            _log_event(task_id, "step_1_inner_text_ready", length=len(text_content))
            
            # Step 2: Find raw text that matches the keyword via LLM (from inner_text)
            matched_texts = _step2_find_matching_text(
                task_id, text_content, intent, is_multi_field, is_attribute_target, keywords, llm
            )
            _log_event(task_id, "step_2_complete", count=len(matched_texts), samples=matched_texts[:3])
            
            if is_attribute_target:
                # Attribute extraction path
                extracted_data = _run_attribute_extraction(
                    task_id, url, intent, matched_texts, html_content, llm, db
                )
            else:
                # Standard regex extraction path
                # Steps 3-4: Find text in raw content (no LLM) -> select best candidate via LLM
                best_snippet = _steps3_4_find_and_select_snippet(
                    task_id, search_content, matched_texts, intent, llm
                )
                
                # Step 5: Generate regex on the best snippet
                _log_event(task_id, "step_5_generate_regex")
                snippet_to_use = best_snippet
                if len(search_content) > 10000 and len(best_snippet) < 4000:
                    if any(ex not in best_snippet for ex in matched_texts):
                        snippet_to_use = search_content[:32000]

                if is_multi_field:
                    extracted_data = _run_multi_field_extraction(
                        task_id, keywords, matched_texts, search_content, snippet_to_use, llm
                    )
                else:
                    extracted_data = _run_single_field_extraction(
                        task_id, url, intent, matched_texts, search_content, 
                        best_snippet, snippet_to_use, llm, db
                    )

        # Persist Results
        if extracted_data:
            db_utils.persist_extraction_result(
                db, task_id, extracted_data=extracted_data, total_matches=len(extracted_data),
                used_parser=used_parser, processing_time_seconds=duration,
                started_at=started, completed_at=completed, used_cached_parser=used_cached
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
