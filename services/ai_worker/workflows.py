
import logging
import json
import re
from typing import List, Dict, Any, Optional, cast

from shared.llm_client import LLMClient
from services.api import db_utils
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

def check_cached_parser(db, domain: str, keywords: List[str], search_content: str, source_type: str = None) -> Dict[str, Any]:
    """Check for and apply cached parser."""
    parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
    
    for p in parsers:
        if source_type and p.source_type != source_type:
            continue
            
        patt, fl = decompose_stored_regex(cast(str, p.generated_regex))
        matches = apply_regex_matches(patt, fl, search_content)
        if matches:
            try:
                db_utils.update_parser_usage(db, p.id)
            except Exception:
                pass
            return {
                "used_parser": p,
                "matches": matches,
                "used_cached": True,
            }
    
    return {"used_parser": None, "matches": [], "used_cached": False}


def run_schema_extraction(
    task_id: str, url: str, schema_fields: List[str], 
    inner_text: str, html_content: str, llm: LLMClient
) -> List[Dict[str, Any]]:
    """Simple schema extraction using LLM."""
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
        return extracted_data
        
    except json.JSONDecodeError as e:
        log_event(task_id, "schema_json_parse_error", error=str(e), response_preview=response[:200] if 'response' in locals() else "")
        return []
    except Exception as e:
        log_event(task_id, "schema_extraction_failed", error=str(e))
        return []


def run_field_extraction(
    task_id: str, url: str, keywords: List[str],
    inner_text: str, html_content: str, llm: LLMClient, db, domain: str
) -> List[Dict[str, Any]]:
    """Simple field extraction using regex generation."""
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
            task_id=task_id,
            target_description=field,
            examples=field_examples,
            snippet=snippet,
            llm=llm,
            max_iterations=2
        )
        
        if result.get("success"):
            pattern = result["final_pattern"]
            flags = result.get("flags", "s")
            matches_with_pos = _get_matches_with_positions(pattern, flags, search_content)
            
            if matches_with_pos:
                log_event(task_id, "field_regex_success", field=field, count=len(matches_with_pos))
                all_matches.extend([{"text": m[0], "field": field, "source": "regex"} for m in matches_with_pos])
                
                # Cache the regex
                try:
                    db_utils.record_new_parser(
                        db, task_id, url, {"keywords": [field]},
                        f"(?{flags}:{pattern})", flags, len(matches_with_pos),
                        "CONTENT", snippet[:2000],
                        [{"text": m[0]} for m in matches_with_pos[:5]]
                    )
                except Exception:
                    pass
    
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
