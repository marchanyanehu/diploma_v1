
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

def _strip_html_to_text(html: str) -> str:
    """Strip HTML tags and normalize whitespace to get clean text."""
    import re as _re
    # Remove HTML tags
    text = _re.sub(r'<[^>]+>', ' ', html)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Normalize whitespace
    text = _re.sub(r'\s+', ' ', text).strip()
    return text

def _looks_like_html(text: str) -> bool:
    """Check if text contains significant HTML tags."""
    import re as _re
    # Count HTML tags
    tag_count = len(_re.findall(r'<[a-zA-Z][^>]*>', text))
    return tag_count >= 2  # At least 2 tags suggests HTML content

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

def _extract_snippet(content: str, idx: int, example_len: int, context: int = 1000) -> str:
    """Extract a snippet from content around a given index with enough context."""
    s_start = max(0, idx - context)
    s_end = min(len(content), idx + example_len + context)
    return content[s_start:s_end]

def _extract_micro_snippet(content: str, idx: int, example_len: int, context: int = 150) -> str:
    """Extract a tiny snippet for debugging - just immediate HTML around example."""
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
        f"I found the following candidate URLs/values.\n\n"
        f"FILTER RULES:\n"
        f"- Keep ONLY values that are specific '{target}' (e.g. individual job posting URLs)\n"
        f"- REMOVE generic navigation links (e.g. '/careers/', '/jobs/', '/about/')\n"
        f"- REMOVE image URLs, javascript links, CSS files\n"
        f"- REMOVE social media share links\n"
        f"- For job URLs: keep URLs with specific job IDs/slugs, remove generic listing pages\n\n"
        f"CANDIDATES: {chunk}\n\n"
        f"Return ONLY a JSON object: {{\"valid_values\": [\"val1\", \"val2\"]}}\n"
        f"Return only the values that are specific '{target}', not navigation links."
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
        
        # Try multiple search strategies for multi-line text
        search_terms = [ex]  # Full text first
        
        # If example has newlines, also try first line and significant chunks
        if '\n' in ex:
            lines = [l.strip() for l in ex.split('\n') if l.strip() and len(l.strip()) > 5]
            if lines:
                search_terms.append(lines[0])  # First line
                # Also try first 2-3 significant words from first line
                words = lines[0].split()
                if len(words) >= 2:
                    search_terms.append(' '.join(words[:3]))
        
        for search_term in search_terms:
            if not search_term or len(search_term) < 3:
                continue
                
            start = 0
            while len(candidates) <= max_candidates:
                idx = raw_content.find(search_term, start)
                if idx == -1:
                    break
                
                snippet = _extract_snippet(raw_content, idx, len(search_term))
                micro = _extract_micro_snippet(raw_content, idx, len(search_term))
                logger.info(f"MICRO_SNIPPET for '{search_term[:30]}': {repr(micro)}")
                
                if snippet not in seen_snippets:
                    candidates.append({
                        "example_match": search_term, 
                        "snippet": snippet, 
                        "micro_snippet": micro,  # Store the micro-snippet too
                        "offset": idx
                    })
                    seen_snippets.add(snippet)
                
                start = idx + 1
                if len(candidates) > 10:
                    break
            
            # If we found candidates with this term, stop trying alternatives
            if candidates:
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


def _check_cached_parser(db, domain: str, keywords: List[str], search_content: str, source_type: str = None) -> Dict[str, Any]:
    """Check for and apply cached parser.
    
    Args:
        db: Database session
        domain: Domain to search parsers for
        keywords: Keywords to match against parser intent
        search_content: Content to apply regex on
        source_type: Optional filter for parser source type (e.g., 'ATTRIBUTE', 'CONTENT')
    """
    parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
    
    for p in parsers:
        # Filter by source_type if specified
        if source_type and p.source_type != source_type:
            continue
            
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
) -> Dict[str, str]:
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
        Dict with 'snippet' (large) and 'micro_snippets' (focused HTML for regex gen)
    """
    # Step 3: Find text in raw content (no LLM, pure string search)
    _log_event(task_id, "step_3_find_in_raw_content", text_count=len(matched_texts))
    candidates = _find_text_in_raw_content(raw_content, matched_texts)
    _log_event(task_id, "step_3_candidates_found", candidate_count=len(candidates))
    
    best_snippet = ""
    micro_snippets = ""
    
    if candidates:
        # Step 4: Provide snippets to LLM, select best candidate
        _log_event(task_id, "step_4_select_best_candidate", candidate_count=len(candidates))
        best = _select_best_candidate_via_llm(candidates, intent, llm)
        best_snippet = best.get("snippet", "")
        
        # Combine all micro-snippets for focused regex generation
        micros = [c.get("micro_snippet", "") for c in candidates if c.get("micro_snippet")]
        micro_snippets = "\n---\n".join(micros[:5])
    
    # Fallback: extract snippet around first matched text
    if not best_snippet:
        snip = extract_snippet_around_example(raw_content, matched_texts[0] if matched_texts else "", max_chars=4000)
        best_snippet = cast(str, snip.get("snippet", ""))
    
    return {"snippet": best_snippet, "micro_snippets": micro_snippets}


def _extract_field_examples(example_texts: List[str], field: str) -> List[str]:
    """Extract field-specific examples from structured examples.
    
    Handles various formats:
    - JSON: {"field": value, ...} or {"field":"value", ...}
    - Text: "Field: Value" lines
    - First line of record (for primary entity like country name)
    """
    import re as _re
    field_examples = []
    field_lower = field.lower().rstrip('s')  # Remove trailing 's' for flexible matching
    
    for ex in example_texts:
        found = False
        
        # Try JSON extraction first (handles {"id": 123, ...} format)
        # Match "field": value or "field":"value"
        json_patterns = [
            rf'"{field_lower}"\s*:\s*"([^"]*)"',  # String value: "field": "value"
            rf'"{field_lower}"\s*:\s*(\d+)',       # Number value: "field": 123
            rf'"{field}"\s*:\s*"([^"]*)"',         # Exact field name string
            rf'"{field}"\s*:\s*(\d+)',             # Exact field name number
        ]
        
        for pattern in json_patterns:
            match = _re.search(pattern, ex, _re.IGNORECASE)
            if match:
                value = match.group(1)
                if value:
                    field_examples.append(value)
                    found = True
                    break
        
        if found:
            continue
            
        # Fallback to text format (Field: Value on separate lines)
        lines = ex.strip().split('\n')
        for line in lines:
            line_lower = line.lower()
            if field_lower in line_lower or field.lower() in line_lower:
                if ':' in line:
                    value = line.split(':', 1)[1].strip()
                    if value:
                        field_examples.append(value)
                        found = True
                else:
                    field_examples.append(line.strip())
                    found = True
                break
        
        # If field is about names/entities and not found, assume first line is the entity name
        if not found and lines:
            name_keywords = ['name', 'title', 'country', 'city', 'company', 'product', 'item']
            if any(kw in field_lower for kw in name_keywords):
                first_line = lines[0].strip()
                if first_line and ':' not in first_line:
                    field_examples.append(first_line)
    
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
            else:
                _log_event(task_id, "field_regex_no_matches", field=field, pattern=pattern)
        else:
            _log_event(task_id, "field_regex_failed", field=field, error=gen.get("error"))
    
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


def _generate_field_regex(field_name: str, examples: List[str], html_content: str, llm: LLMClient) -> Optional[Dict[str, str]]:
    """Generate a regex pattern for a single field based on examples found in HTML."""
    import re
    
    if not examples:
        return None
    
    # Find where examples appear in HTML to get context
    snippets = []
    for ex in examples[:3]:  # Use first 3 examples
        if not ex:
            continue
        idx = html_content.find(str(ex))
        if idx != -1:
            start = max(0, idx - 100)
            end = min(len(html_content), idx + len(str(ex)) + 100)
            snippets.append(html_content[start:end])
    
    if not snippets:
        return None
    
    # Ask LLM to generate regex
    snippet_text = "\n---\n".join(snippets[:3])
    prompt = f"""Generate a regex to extract "{field_name}" values from HTML.

EXAMPLE VALUES TO MATCH:
{chr(10).join(f'- {ex}' for ex in examples[:5])}

HTML SNIPPETS WHERE THESE VALUES APPEAR:
{snippet_text}

INSTRUCTIONS:
1. Create a regex that captures these values from the HTML structure.
2. Use a single capturing group for the target value.
3. The regex should be general enough to match similar items on the page.
4. Output ONLY a JSON object with "regex" and "flags" keys.

Example output: {{"regex": "<span class=\\"price\\">\\\\$([\\\\d.]+)</span>", "flags": "s"}}"""

    try:
        messages = [
            {"role": "system", "content": "You are a regex expert. Generate precise regex patterns to extract data from HTML. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ]
        raw = llm.chat(messages, temperature=0.1)
        
        # Parse response
        match = re.search(r'\{[^{}]*"regex"[^{}]*\}', raw, re.DOTALL)
        if match:
            result = _json.loads(match.group(0))
            return {"regex": result.get("regex", ""), "flags": result.get("flags", "s")}
    except Exception as e:
        logger.warning(f"Failed to generate regex for {field_name}: {e}")
    
    return None


def _run_schema_extraction_with_cache(
    task_id: str, url: str, schema_fields: List[str], inner_text: str, 
    html_content: str, llm: LLMClient, db, domain: str
) -> tuple[List[Dict[str, Any]], bool]:
    """Extract data with LLM, then generate and cache regexes for reuse.
    
    Hybrid approach:
    1. First extraction: LLM extracts all values
    2. Generate regex patterns based on extracted values
    3. Cache the patterns for future requests
    4. Future requests: Use cached regex (no LLM needed)
    
    Returns:
        Tuple of (extracted_data, used_cached_parser)
    """
    import re
    
    _log_event(task_id, "schema_extraction_start", fields=schema_fields)
    
    # Check for cached schema regex first
    cached_parsers = db_utils.find_cached_parser(db, domain, keywords=schema_fields) if db else []
    
    for parser in cached_parsers:
        try:
            stored_regex = cast(str, parser.generated_regex)
            
            # Check if this is a SCHEMA-type parser (stores field regexes as JSON)
            if "SCHEMA:" in stored_regex:
                _log_event(task_id, "schema_cache_found", parser_id=parser.id)
                
                # Extract the JSON schema data
                schema_match = re.search(r'SCHEMA:(\{.*\})', stored_regex)
                if not schema_match:
                    continue
                
                try:
                    schema_data = _json.loads(schema_match.group(1))
                    field_regexes = schema_data.get("field_regexes", {})
                except _json.JSONDecodeError:
                    continue
                
                if not field_regexes:
                    continue
                
                # Apply each field's regex to extract values
                field_matches = {}
                for field, regex_info in field_regexes.items():
                    pattern = regex_info.get("regex", "")
                    flags = regex_info.get("flags", "s")
                    if pattern:
                        matches = _apply_regex_matches(pattern, flags, html_content)
                        if matches:
                            # Clean HTML from matches
                            cleaned = []
                            for m in matches:
                                clean = _strip_html_to_text(m) if _looks_like_html(m) else m
                                if clean:
                                    cleaned.append(clean)
                            if cleaned:
                                field_matches[field] = cleaned
                                _log_event(task_id, "schema_field_cache_hit", field=field, count=len(cleaned))
                
                # Combine field matches into records
                if field_matches:
                    max_len = max(len(v) for v in field_matches.values())
                    extracted_data = []
                    
                    for i in range(max_len):
                        record = {}
                        for field, values in field_matches.items():
                            if i < len(values):
                                record[field] = values[i]
                        
                        if record:
                            text_repr = " | ".join(f"{k}: {v}" for k, v in record.items() if v)
                            extracted_data.append({
                                "text": text_repr,
                                "fields": record,
                                "source": "cached_schema_regex",
                                "confidence": 0.95
                            })
                    
                    if extracted_data:
                        _log_event(task_id, "schema_cache_hit", parser_id=parser.id, record_count=len(extracted_data))
                        # Update parser usage stats
                        try:
                            db_utils.update_parser_usage(db, parser.id)
                        except Exception as e:
                            _log_event(task_id, "update_parser_usage_failed", error=str(e))
                        return extracted_data, True  # Cache was used
            
        except Exception as e:
            logger.warning(f"Failed to apply cached schema parser: {e}")
    
    _log_event(task_id, "schema_cache_miss", generating_new=True)
    
    # No cache hit - use LLM extraction
    fields_list = ", ".join(schema_fields)
    prompt = f"""Extract the following fields from the page content:
FIELDS TO EXTRACT: {fields_list}

PAGE CONTENT:
{inner_text[:15000]}

INSTRUCTIONS:
1. Find ALL items/records that match the requested fields.
2. If there are MULTIPLE items (like a list of products, jobs, etc.), return a JSON array with ALL of them.
3. For each item, extract the EXACT values from the page content.
4. If a field is not found for an item, use empty string.
5. Return ONLY valid JSON - either an array of objects OR a single object.

Example for MULTIPLE items:
{{"items": [{{"name": "Product 1", "price": "$10"}}, {{"name": "Product 2", "price": "$20"}}]}}

Example for SINGLE item:
{{"job_title": "Software Engineer", "city": "New York"}}

Return ONLY the JSON, no other text."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a data extraction assistant. Extract ALL structured data from web page content. "
                "If there are multiple items, return them ALL as a JSON array. Output ONLY valid JSON."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    raw_response = llm.chat(
        messages,
        temperature=0.1,
        extra_params={"response_format": {"type": "json_object"}},
    )
    _log_event(task_id, "schema_llm_response", response=raw_response[:500])

    # Parse the JSON response
    parsed_data = None
    try:
        parsed_data = _json.loads(raw_response)
    except _json.JSONDecodeError:
        array_match = re.search(r"\[[\s\S]*\]", raw_response)
        if array_match:
            try:
                parsed_data = _json.loads(array_match.group(0))
            except Exception:
                parsed_data = None
        if parsed_data is None:
            obj_match = re.search(r"\{[\s\S]*\}", raw_response)
            if obj_match:
                try:
                    parsed_data = _json.loads(obj_match.group(0))
                except Exception:
                    parsed_data = None

    if parsed_data is None:
        _log_event(task_id, "schema_extraction_failed", error="Could not parse JSON response")
        return [], False

    # Normalize to list of records
    records = []
    if isinstance(parsed_data, list):
        records = parsed_data
    elif isinstance(parsed_data, dict):
        if "items" in parsed_data and isinstance(parsed_data["items"], list):
            records = parsed_data["items"]
        elif any(k in parsed_data for k in ["data", "results", "records", "list"]):
            for key in ["data", "results", "records", "list"]:
                if key in parsed_data and isinstance(parsed_data[key], list):
                    records = parsed_data[key]
                    break
        else:
            records = [parsed_data]

    _log_event(task_id, "schema_records_found", count=len(records))

    # Build result records
    extracted_data = []
    field_examples = {field: [] for field in schema_fields}

    # Heuristic: collect image URLs from page to use as examples (no positional assignment)
    image_urls_from_page: List[str] = []
    if "image_url" in schema_fields and html_content:
        import re as _re
        img_pattern = r'<img[^>]+(?:data-src|src)\s*=\s*"([^"]+)"'
        image_urls_from_page = _re.findall(img_pattern, html_content, flags=_re.IGNORECASE)
        # Preserve order, dedupe while keeping first occurrences
        seen_imgs = set()
        ordered_imgs: List[str] = []
        for u in image_urls_from_page:
            if u not in seen_imgs:
                ordered_imgs.append(u)
                seen_imgs.add(u)
        image_urls_from_page = ordered_imgs
        
    for record in records:
        if not isinstance(record, dict):
            continue
        
        # Collect examples for each field (for regex generation)
        for field in schema_fields:
            if field in record and record[field]:
                field_examples[field].append(str(record[field]))
        
        # For URL fields, try to extract from HTML if not found
        for field in schema_fields:
            if 'url' in field.lower() and (not record.get(field) or record.get(field) == ""):
                apply_pattern = r'href=["\']([^"\']*(?:apply|career|job)[^"\']*)["\']'
                apply_matches = re.findall(apply_pattern, html_content, re.IGNORECASE)
                if apply_matches:
                    full_urls = [u for u in apply_matches if u.startswith('http')]
                    record[field] = full_urls[0] if full_urls else apply_matches[0]

        # Do not positional-fill image_url; only use as regex examples
        if "image_url" in schema_fields and record.get("image_url"):
            field_examples["image_url"].append(str(record["image_url"]))

    # If image_url examples were missing in records, seed examples from page-level images for regex generation
    if "image_url" in schema_fields and not field_examples.get("image_url") and image_urls_from_page:
        field_examples["image_url"].extend(image_urls_from_page[:5])
        
        # Generate and cache regex patterns for future use AND use regex results as output
        field_regexes = {}
        if len(records) >= 1:
            _log_event(task_id, "schema_generating_regex", field_count=len(schema_fields))
            for field, examples in field_examples.items():
                if examples:
                    regex_result = _generate_field_regex(field, examples, html_content, llm)
                    if regex_result and regex_result.get("regex"):
                        field_regexes[field] = regex_result
                        _log_event(task_id, "schema_field_regex_generated", field=field)

        if not field_regexes:
            _log_event(task_id, "schema_extraction_failed", error="regex_generation_failed")
            return [], False

        # Apply generated regexes to produce final extraction (regex-only)
        field_matches: Dict[str, List[str]] = {}
        for field, regex_info in field_regexes.items():
            pattern = regex_info.get("regex", "")
            flags = regex_info.get("flags", "s")
            if pattern:
                matches = _apply_regex_matches(pattern, flags, html_content)
                if matches:
                    cleaned = []
                    for m in matches:
                        clean = _strip_html_to_text(m) if _looks_like_html(m) else m
                        if clean:
                            cleaned.append(clean)
                    if cleaned:
                        field_matches[field] = cleaned

        if not field_matches:
            _log_event(task_id, "schema_extraction_failed", error="regex_no_matches")
            return [], False

        max_len = max(len(v) for v in field_matches.values())
        extracted_via_regex: List[Dict[str, Any]] = []
        for i in range(max_len):
            record = {}
            for field, values in field_matches.items():
                if i < len(values):
                    record[field] = values[i]
            if record:
                text_repr = " | ".join(f"{k}: {v}" for k, v in record.items() if v)
                extracted_via_regex.append(
                    {"text": text_repr, "fields": record, "source": "schema_regex", "confidence": 0.9}
                )

        if not extracted_via_regex:
            _log_event(task_id, "schema_extraction_failed", error="regex_combination_empty")
            return [], False

        # Cache the combined regexes
        combined_pattern = _json.dumps({"schema_fields": schema_fields, "field_regexes": field_regexes})
        try:
            db_utils.record_new_parser(
                db,
                task_id=task_id,
                url=url,
                intent={"keywords": schema_fields, "schema_fields": schema_fields},
                pattern=f"(?s:SCHEMA:{combined_pattern})",
                flags="s",
                matches_count=len(extracted_via_regex),
                source_type="SCHEMA",
                sample_input=html_content[:2000],
                sample_output=[{"text": d["text"]} for d in extracted_via_regex[:5]],
            )
            _log_event(task_id, "schema_regex_cached", fields=list(field_regexes.keys()))
        except Exception as e:
            logger.warning(f"Failed to cache schema regex: {e}")

        _log_event(task_id, "schema_extraction_success", record_count=len(extracted_via_regex))
        return extracted_via_regex, False  # Not from cache - newly extracted

def _run_schema_extraction(
    task_id: str, schema_fields: List[str], inner_text: str, html_content: str, llm: LLMClient
) -> List[Dict[str, Any]]:
    """Wrapper for backwards compatibility - calls the new function without caching."""
    result, _ = _run_schema_extraction_with_cache(
        task_id, "", schema_fields, inner_text, html_content, llm, None, ""
    )
    return result


def _run_attribute_extraction(
    task_id: str, url: str, intent: Dict, text_examples: List[str],
    html_content: str, llm: LLMClient, db
) -> List[Dict[str, Any]]:
    """Extract attributes from HTML using unified regex approach with caching.
    
    Uses the same regex generation and caching pipeline as content extraction,
    but optimized for attribute values (href, src, etc.).
    """
    import re as _re
    
    target = intent.get("target", "") or "target data"
    attribute = intent.get("target_attribute", "") or "href"  # default to href if missing
    domain = urlparse(url).netloc
    
    _log_event(task_id, "attribute_extraction_start", attribute=attribute, text_examples=text_examples[:3])
    
    # Step 1: Check for cached ATTRIBUTE parser first
    cache_result = _check_cached_parser(db, domain, intent.get("keywords", []), html_content, source_type="ATTRIBUTE")
    if cache_result["used_cached"] and cache_result["matches"]:
        _log_event(task_id, "attribute_using_cached_parser", parser_id=cache_result["used_parser"].id, match_count=len(cache_result["matches"]))
        # Update parser usage stats
        db_utils.update_parser_usage(db, cache_result["used_parser"].id)
        return [{"text": v, "source": "cached_attribute_regex", "confidence": 1.0} for v in cache_result["matches"]]
    
    # Step 2: Generate STRUCTURAL regex for attribute extraction via LLM
    # Key: The regex must match the HTML STRUCTURE, not the specific text content!
    _log_event(task_id, "attribute_generating_regex")
    
    # Find HTML snippets containing the text examples for context
    snippets = []
    for ex in text_examples[:5]:
        idx = html_content.lower().find(ex.lower())
        if idx != -1:
            snippet = _extract_snippet(html_content, idx, len(ex), context=500)
            snippets.append(snippet)
    
    if not snippets:
        snippets = [html_content[:15000]]
    
    combined_snippet = "\n---\n".join(snippets[:3])[:15000]
    
    # Ask LLM to generate a STRUCTURAL regex - NOT content-based!
    regex_prompt = (
        f"Analyze this HTML and generate a regex to extract '{attribute}' attribute values for '{target}'.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"1. The regex must match the HTML STRUCTURE/PATTERN, NOT the specific text content\n"
        f"2. DO NOT include any specific text like job titles, names, or dynamic content in the regex\n"
        f"3. Match based on: tag names, CSS classes, parent elements, attribute patterns\n"
        f"4. The regex should work even when the page content changes (new jobs, products, etc.)\n"
        f"5. Capture ONLY the '{attribute}' attribute value\n\n"
        f"Example of WRONG regex: <a href=\"([^\"]+)\"[^>]*>.*?Senior Developer.*?</a>\n"
        f"Example of CORRECT regex: <a[^>]*class=\"job-link\"[^>]*href=\"([^\"]+)\"[^>]*>\n\n"
        f"The visible text in target elements includes (for context only, DO NOT embed in regex):\n"
        f"{text_examples[:3]}\n\n"
        f"HTML SAMPLE:\n{combined_snippet}\n\n"
        f"Analyze the HTML structure around these elements and create a STRUCTURAL pattern.\n"
        f"Return ONLY a JSON object:\n"
        f'{{"regex": "structural_pattern", "flags": "is", "explanation": "what structural pattern you identified"}}'
    )
    
    pattern = None
    flags = "is"
    
    try:
        resp = llm.generate_text(regex_prompt, extra_params={"response_format": {"type": "json_object"}})
        data = _json.loads(resp)
        pattern = data.get("regex")
        flags = data.get("flags", "is")
        _log_event(task_id, "attribute_regex_generated", pattern=pattern[:100] if pattern else None)
        
        # VALIDATION: Reject patterns that contain specific example text (content-bound)
        if pattern:
            pattern_lower = pattern.lower()
            for ex in text_examples[:5]:
                # Check if any significant part of the example text is embedded in the regex
                ex_words = [w for w in ex.lower().split() if len(w) > 4]  # Words > 4 chars
                for word in ex_words:
                    if word in pattern_lower and word not in ('href', 'class', 'data', 'link', 'item'):
                        _log_event(task_id, "attribute_regex_rejected_content_bound", 
                                   pattern=pattern[:80], embedded_word=word)
                        pattern = None  # Reject this pattern, fall back to heuristic
                        break
                if pattern is None:
                    break
                    
    except Exception as e:
        _log_event(task_id, "attribute_regex_generation_failed", error=str(e))
    
    extracted_values = []
    used_pattern = None
    
    # Step 3: Try LLM-generated STRUCTURAL regex first (only if it passed validation)
    if pattern:
        matches = _apply_regex_matches(pattern, flags, html_content)
        if matches:
            extracted_values = matches
            used_pattern = pattern
            _log_event(task_id, "attribute_llm_regex_success", match_count=len(matches))
    
    # Step 4: Fallback to simple heuristic regex if LLM pattern failed
    if not extracted_values:
        _log_event(task_id, "attribute_fallback_to_heuristic")
        extracted_values = _extract_attribute_from_html_by_text(html_content, text_examples, attribute)
        if extracted_values:
            # DON'T cache overly generic patterns - they require LLM filtering anyway
            # Mark as heuristic-based (not worth caching)
            used_pattern = None  # Don't cache generic patterns
            _log_event(task_id, "attribute_heuristic_success", match_count=len(extracted_values))
    
    # Step 5: Final fallback to LLM direct extraction
    if not extracted_values:
        _log_event(task_id, "attribute_fallback_to_llm_direct")
        extracted_values = _extract_attribute_via_llm(html_content, text_examples, target, attribute, llm)
    
    extracted_data = []
    if extracted_values:
        # Filter values via LLM to remove noise
        filtered_values = _filter_values_via_llm(extracted_values, target, llm)
        unique_values = list(dict.fromkeys(filtered_values))  # Preserve order, dedupe
        
        if unique_values:
            # Only cache STRUCTURAL patterns (LLM-generated that passed validation)
            # Don't cache generic heuristic patterns that need LLM filtering
            if used_pattern and len(unique_values) >= 1:
                # Verify pattern is specific enough (has class, id, or specific tag attributes)
                is_specific = any(x in used_pattern.lower() for x in ['class=', 'id=', 'data-', 'role=', 'type='])
                if is_specific:
                    try:
                        db_utils.record_new_parser(
                            db,
                            task_id=task_id,
                            url=url,
                            intent=intent,
                            pattern=used_pattern,
                            flags=flags,
                            matches_count=len(unique_values),
                            source_type="ATTRIBUTE",
                            sample_input=combined_snippet[:2000],
                            sample_output=[{"text": v, "attribute": attribute} for v in unique_values[:5]]
                        )
                        _log_event(task_id, "attribute_parser_cached", pattern=used_pattern[:80])
                    except Exception as e:
                        _log_event(task_id, "attribute_parser_cache_failed", error=str(e))
                else:
                    _log_event(task_id, "attribute_pattern_too_generic_not_cached", pattern=used_pattern[:80])
            
            extracted_data = [{"text": v, "source": f"{attribute}_regex", "confidence": 0.95} for v in unique_values]
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
    
    # Log detailed attempt info for debugging
    for i, att in enumerate(gen.get("attempts", [])):
        val = att.get("validation", {})
        _log_event(task_id, f"regex_attempt_{i}", 
                   pattern=str(att.get("parsed", {}).get("regex", ""))[:100],
                   matches_count=len(val.get("matches", [])),
                   match_samples=val.get("matches", [])[:3],
                   issues=val.get("issues", []),
                   missing=val.get("missing_examples", []))
    
    extracted_data = []
    if gen.get("success"):
        pattern = gen.get("final_pattern")
        flags = gen.get("final_flags", "s")
        matches = _apply_regex_matches(pattern, flags, search_content)
        
        if matches:
            # Post-process: if matches contain HTML, strip to text
            processed_matches = []
            for m in matches:
                if _looks_like_html(m):
                    clean_text = _strip_html_to_text(m)
                    if clean_text and len(clean_text) > 3:  # Skip empty/trivial
                        processed_matches.append(clean_text)
                else:
                    processed_matches.append(m)
            
            unique_matches = list(dict.fromkeys(processed_matches))  # Dedupe
            
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

        # Persist sources (including html_content for normalized schema)
        try:
            db_utils.update_task_sources(db, task_id, page_content=inner_text[:200000],
                                         html_content=html_content[:200000] if html_content else None,
                                         network_requests=network, intent=intent, started_at=started)
        except Exception as e:
            logger.warning(f"Failed to persist sources: {e}")

        llm = LLMClient.from_env()
        domain = urlparse(url).netloc
        keywords = intent.get("keywords", [])
        schema_fields = intent.get("schema_fields", [])
        
        # Detect target type and prepare content
        # We rely on the intent extractor to tell us if this is an attribute extraction
        target_attribute = intent.get("target_attribute")
        is_attribute_target = bool(target_attribute) or intent.get("source_type") == "attribute"
        # Fallback: if source_type is attribute but no attribute specified, default to href (most common)
        if is_attribute_target and not target_attribute:
            target_attribute = "href"
        
        # Schema-based extraction takes priority
        is_schema_extraction = len(schema_fields) >= 2
        
        # Also detect multi-field (when no schema but multiple keywords)
        is_multi_field = len(keywords) >= 3 and not is_attribute_target and not is_schema_extraction
        
        _log_event(task_id, "target_type_detected", 
                   is_schema_extraction=is_schema_extraction,
                   schema_fields=schema_fields,
                   is_multi_field=is_multi_field, 
                   is_attribute_target=is_attribute_target, 
                   target_attribute=target_attribute)
        
        content = _prepare_search_content(inner_text, html_content)
        text_content = content["text_content"]
        search_content = content["search_content"]

        # Check for cached parser (now unified for both content and attribute targets)
        cache_result = {"used_parser": None, "matches": [], "used_cached": False}
        source_type_filter = "ATTRIBUTE" if is_attribute_target else None
        cache_result = _check_cached_parser(db, domain, keywords, search_content if not is_attribute_target else html_content, source_type=source_type_filter)
        used_parser = cache_result["used_parser"]
        used_cached = cache_result["used_cached"]
        
        extracted_data = []
        
        # SCHEMA-BASED EXTRACTION (highest priority)
        if is_schema_extraction and schema_fields:
            _log_event(task_id, "using_schema_extraction", fields=schema_fields)
            schema_result = _run_schema_extraction_with_cache(
                task_id, url, schema_fields, inner_text, html_content, llm, db, domain
            )
            extracted_data, schema_used_cache = schema_result
            if schema_used_cache:
                used_cached = True  # Mark that cached parser was used
            if extracted_data:
                _log_event(task_id, "schema_extraction_complete", count=len(extracted_data))
        
        if cache_result["matches"] and not extracted_data:
            extracted_data = [{"text": m, "source": "cached_regex", "confidence": 1.0} for m in cache_result["matches"]]
            # Update parser usage stats when cache is used
            if cache_result["used_parser"]:
                try:
                    db_utils.update_parser_usage(db, cache_result["used_parser"].id)
                except Exception as e:
                    _log_event(task_id, "update_parser_usage_failed", error=str(e))
        elif not extracted_data:
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
            
            # FALLBACK: If attribute extraction found nothing (or wasn't attempted),
            # assume the content is not standard HTML (e.g. JSON, XML) or the attribute approach failed.
            # Switch to Universal Regex Generation (treating content as text).
            if not extracted_data and not is_multi_field:
                _log_event(task_id, "fallback_to_generic_regex")
                
                # If we previously looked for anchors (is_attribute_target=True), we need to re-run Step 2
                # to find the ACTUAL values (e.g. the URLs themselves), not the anchors.
                if is_attribute_target:
                    matched_texts = _step2_find_matching_text(
                        task_id, text_content, intent, is_multi_field, False, keywords, llm
                    )
                    _log_event(task_id, "step_2_retry_complete", count=len(matched_texts))

                # Steps 3-4: Find text in raw content (no LLM) -> select best candidate via LLM
                snippet_result = _steps3_4_find_and_select_snippet(
                    task_id, search_content, matched_texts, intent, llm
                )
                best_snippet = snippet_result.get("snippet", "")
                micro_snippets = snippet_result.get("micro_snippets", "")
                
                # Step 5: Generate regex - use micro_snippets (focused HTML) if available
                _log_event(task_id, "step_5_generate_regex", 
                           snippet_len=len(best_snippet),
                           micro_len=len(micro_snippets),
                           micro_preview=micro_snippets[:300] if micro_snippets else "")
                
                # Prefer micro_snippets for regex gen (cleaner, focused HTML)
                snippet_to_use = micro_snippets if micro_snippets else best_snippet
                if not snippet_to_use or len(snippet_to_use) < 50:
                    snippet_to_use = best_snippet if best_snippet else search_content[:32000]

                extracted_data = _run_single_field_extraction(
                    task_id, url, intent, matched_texts, search_content, 
                    best_snippet, snippet_to_use, llm, db
                )
                
            elif is_multi_field and not extracted_data:
                 extracted_data = _run_multi_field_extraction(
                    task_id, keywords, matched_texts, search_content, search_content[:32000], llm
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
