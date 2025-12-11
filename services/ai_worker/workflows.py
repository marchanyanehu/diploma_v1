
import logging
import json
import re
from typing import List, Dict, Any, Optional, cast

from .llm_client import LLMClient
import shared.database as db_utils
from . import regex_generation
from .prompts import (
    SCHEMA_EXTRACTION_SYSTEM_PROMPT,
    SCHEMA_EXTRACTION_USER_TEMPLATE,
)
from .utils import (
    log_event, decompose_stored_regex, apply_regex_matches, 
    strip_html_to_text
)

logger = logging.getLogger(__name__)

def check_cached_parser(
    db, domain: str, fields: List[str], search_content: str, 
    source_type: str = "SEMANTIC", min_matches: int = 1, url_pattern: Optional[str] = None
) -> Dict[str, Any]:
    """Check for and apply cached regex parser based on domain + complete URL + fields.
    
    Args:
        db: Database session
        domain: Domain name (e.g., 'puko.lt')
        fields: List of field names to extract (e.g., ['title', 'price'])
        search_content: Content to search (semantic text or HTML)
        source_type: Type of content ('SEMANTIC', 'HTML', 'JSON')
        min_matches: Minimum matches required to consider cache valid
        url_pattern: Complete URL (e.g., 'https://puko.lt/category/robes') for precise matching
        
    Returns:
        Dict with used_parser, matches, and used_cached flag
    """
    # Find cached parsers for this domain + complete URL + field combination
    parsers = db_utils.find_cached_parser_by_fields(db, domain, fields, source_type, url_pattern=url_pattern)
    
    for p in parsers:
        patt, fl = decompose_stored_regex(cast(str, p.generated_regex))
        matches = apply_regex_matches(patt, fl, search_content)
        
        # Validate: enough matches and fields present
        if matches and len(matches) >= min_matches:
            # Check if all requested fields are in the matches
            if matches[0].get("fields"):
                matched_fields = set(matches[0]["fields"].keys())
                if set(fields).issubset(matched_fields):
                    try:
                        db_utils.update_parser_usage(db, p.id)
                        logger.info(f"Cache hit: parser_id={p.id}, domain={domain}, fields={fields}")
                    except Exception:
                        pass
                    return {
                        "used_parser": p,
                        "matches": matches,
                        "used_cached": True,
                    }
        
        # Cache invalid - invalidate and remove
        logger.info(f"Cache invalid: parser_id={p.id}, domain={domain}, match_count={len(matches) if matches else 0}")
        try:
            db_utils.invalidate_parser(db, p.id)
        except Exception as e:
            logger.warning(f"Failed to invalidate parser {p.id}: {e}")
    
    return {"used_parser": None, "matches": [], "used_cached": False}


def run_schema_extraction(
    task_id: str, url: str, schema_fields: List[str], 
    inner_text: str, html_content: str, llm: LLMClient,
    db = None, domain: str = None, url_pattern: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Schema extraction with semantic content + regex caching.
    
    Workflow:
    1. Check cache for domain + URL pattern + fields
    2. If cache hit: apply regex to semantic content (fast)
    3. If cache miss: LLM extraction → generate regex → cache it
    4. If cache invalid: remove + regenerate
    """
    # Prefer clean inner_text for structured extraction (better signal-to-noise)
    # HTML contains too much layout markup that confuses the LLM
    content = inner_text if inner_text and len(inner_text) > 500 else html_content
    content_snippet = content[:150000]  # Limit for LLM - increased to capture more items
    
    fields_list = ", ".join(schema_fields)
    prompt = SCHEMA_EXTRACTION_USER_TEMPLATE.format(
        fields_list=fields_list,
        content_snippet=content_snippet
    )
    
    try:
        response = llm.chat([
            {"role": "system", "content": SCHEMA_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])
        
        log_event(task_id, "schema_llm_raw_response", response=response[:500])
        
        # Try to extract JSON from response (in case LLM wrapped it in markdown)
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
        
        data = json.loads(response)
        log_event(task_id, "schema_llm_parsed", keys=list(data.keys()))
        
        # Handle both array and single object responses
        items = data.get("items", [data] if any(f in data for f in schema_fields) else [])
        
        if not items:
            log_event(task_id, "schema_no_items")
            return []
        
        # Convert to standard format
        extracted_data = []
        for item in items:
            text_repr = " | ".join(f"{k}: {v}" for k, v in item.items() if v)
            extracted_data.append({
                "text": text_repr,
                "fields": item,
                "source": "schema_extraction",
                "confidence": 0.9
            })
        
        log_event(task_id, "schema_extraction_success", count=len(extracted_data))
        
        # Generate and cache regex pattern from semantic content
        if db and domain and extracted_data:
            try:
                _cache_regex_from_extraction(
                    db, task_id, domain, schema_fields, 
                    content_snippet, extracted_data, llm, url_pattern=url_pattern
                )
            except Exception as e:
                logger.warning(f"Failed to cache regex: {e}")
        
        return extracted_data
        
    except json.JSONDecodeError as e:
        log_event(task_id, "schema_json_parse_error", error=str(e), response_preview=response[:200] if 'response' in locals() else "")
        return []
    except Exception as e:
        log_event(task_id, "schema_extraction_failed", error=str(e))
        return []


def _cache_regex_from_extraction(
    db, task_id: str, domain: str, fields: List[str],
    semantic_content: str, extracted_items: List[Dict], llm: LLMClient,
    url_pattern: Optional[str] = None
) -> None:
    """Generate regex pattern from successful extraction and cache it.
    
    Takes the semantic content and extracted items, asks LLM to generate
    a regex pattern that can extract the same data, then caches it.
    """
    if len(extracted_items) < 2:
        log_event(task_id, "regex_cache_skip", reason="too_few_items")
        return
    
    # Extract examples from semantic content by finding the actual text
    # Get first 3-5 items as examples
    examples = []
    for item in extracted_items[:5]:
        field_vals = item.get("fields", {})
        if not field_vals:
            continue
        
        # For single field, just use the value
        if len(fields) == 1:
            val = field_vals.get(fields[0], "")
            if val and isinstance(val, str):
                examples.append(val.strip())
        else:
            # For multiple fields, find the pattern in semantic content
            # Look for the first field value in content
            first_field = fields[0]
            first_val = field_vals.get(first_field, "")
            if first_val:
                # Find this value in semantic content with surrounding context
                idx = semantic_content.find(str(first_val)[:30])
                if idx >= 0:
                    # Extract ~200 chars around it to capture the pattern
                    start = max(0, idx - 50)
                    end = min(len(semantic_content), idx + 150)
                    pattern_sample = semantic_content[start:end].strip()
                    examples.append(pattern_sample)
    
    if len(examples) < 2:
        log_event(task_id, "regex_cache_skip", reason="insufficient_examples")
        return
    
    # Get snippet with examples (max 5000 chars around first example)
    first_example = examples[0]
    snippet_start = semantic_content.find(first_example[:50]) if first_example else 0
    snippet_start = max(0, snippet_start - 500)
    snippet = semantic_content[snippet_start:snippet_start + 5000]
    
    try:
        # Use existing regex generation with semantic content
        result = regex_generation.iterative_regex_generation(
            source=semantic_content,
            examples=examples,
            target_desc=f"Extract items with fields: {', '.join(fields)}",
            llm=llm,
            snippet=snippet,
            max_iterations=2
        )
        
        if result.get("success") and result.get("final_pattern"):
            pattern = result["final_pattern"]
            flags = result.get("final_flags", "")
            stored_regex = f"(?{flags}){pattern}" if flags else pattern
            
            # Estimate confidence from attempts
            attempts = result.get("attempts", [])
            confidence = 0.9 if len(attempts) == 1 else 0.7
            
            # Store in cache with field-based indexing
            db_utils.create_parser_cache_by_fields(
                db=db,
                domain=domain,
                fields=fields,
                generated_regex=stored_regex,
                source_type="SEMANTIC",
                created_by_task_id=task_id,
                test_matches_count=len(extracted_items),
                confidence_score=int(confidence * 100),
                url_pattern=url_pattern,
                sample_input=snippet,
                sample_output=extracted_items[:10]
            )
            log_event(task_id, "regex_cached", domain=domain, fields=fields, 
                     pattern_len=len(pattern), attempts=len(attempts))
        else:
            # Get failure reason from attempts
            attempts = result.get("attempts", [])
            last_attempt = attempts[-1] if attempts else {}
            last_validation = last_attempt.get("validation", {})
            error = last_validation.get("error") or result.get("error") or "unknown"
            
            log_event(task_id, "regex_generation_failed", 
                     success=False, error=error, attempts=len(attempts))
            
    except Exception as e:
        logger.warning(f"Regex generation/caching failed: {e}")
        log_event(task_id, "regex_cache_error", error=str(e))


def run_field_extraction(
    task_id: str, keywords: List[str],
    inner_text: str, html_content: str, llm: LLMClient, db, domain: str,
    url_pattern: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Simple field extraction using regex generation with field-based caching."""
    search_content = html_content if html_content else inner_text
    
    # Ask LLM to find examples first
    target = " + ".join(keywords)
    snippet = inner_text[:5000]
    
    prompt = f"""Find 3-5 examples of "{target}" from this content.
Return ONLY JSON: {{"examples": ["example1", "example2", ...]}}

CONTENT:
{snippet}"""
    
    try:
        response = llm.chat([
            {"role": "system", "content": "You extract examples from text. Output only JSON."},
            {"role": "user", "content": prompt}
        ])
        examples_data = json.loads(response)
        examples = examples_data.get("examples", keywords[:3])
        
        if not examples:
            examples = keywords[:3]
            
        log_event(task_id, "found_examples", count=len(examples), examples=examples[:3])
        
    except Exception as e:
        log_event(task_id, "example_finding_failed", error=str(e))
        examples = keywords[:3]
    
    # Generate regex for each field
    all_matches = []
    for field in keywords:
        field_examples = [ex for ex in examples if field.lower() in ex.lower()][:3]
        if not field_examples:
            field_examples = [field]
        
        # Use snippet around first example
        if field_examples[0] in search_content:
            idx = search_content.find(field_examples[0])
            snippet_start = max(0, idx - 2000)
            snippet_end = min(len(search_content), idx + 2000)
            snippet = search_content[snippet_start:snippet_end]
        else:
            snippet = search_content[:4000]
        
        # Generate regex
        result = regex_generation.iterative_regex_generation(
            source=search_content,
            examples=field_examples,
            target_desc=field,
            llm=llm,
            snippet=snippet,
            max_iterations=2
        )
        
        if result.get("success"):
            pattern = result["final_pattern"]
            flags = result.get("final_flags", "s")
            matches_with_pos = _get_matches_with_positions(pattern, flags, search_content)
            
            if matches_with_pos:
                log_event(task_id, "field_regex_success", field=field, count=len(matches_with_pos))
                all_matches.extend([{"text": m[0], "field": field, "source": "regex"} for m in matches_with_pos])
                
                # Cache the regex using field-based caching
                if db and domain:
                    try:
                        stored_regex = f"(?{flags}){pattern}" if flags else pattern
                        db_utils.create_parser_cache_by_fields(
                            db=db,
                            domain=domain,
                            fields=[field],
                            generated_regex=stored_regex,
                            source_type="SEMANTIC",
                            created_by_task_id=task_id,
                            test_matches_count=len(matches_with_pos),
                            confidence_score=85,
                            url_pattern=url_pattern,
                            sample_input=snippet[:2000],
                            sample_output=[{"text": m[0]} for m in matches_with_pos[:10]]
                        )
                    except Exception as cache_err:
                        logger.warning(f"Failed to cache field regex: {cache_err}")
    
    if all_matches:
        log_event(task_id, "field_extraction_success", count=len(all_matches))
        return [{"text": m["text"], "source": "field_extraction", "confidence": 0.85} for m in all_matches]
    
    return []


def _get_matches_with_positions(pattern: str, flags: str, content: str) -> List[tuple]:
    """Get regex matches with their start positions in content."""
    re_flags = 0
    for f in flags:
        if f == 'i':
            re_flags |= re.IGNORECASE
        elif f == 'm':
            re_flags |= re.MULTILINE
        elif f == 's':
            re_flags |= re.DOTALL
    
    matches_with_pos = []
    try:
        compiled = re.compile(pattern, re_flags)
        for m in compiled.finditer(content):
            text = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            text = text.strip()
            if text:
                matches_with_pos.append((text, m.start()))
    except re.error:
        pass
    return matches_with_pos
