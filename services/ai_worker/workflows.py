
import logging
import json
import re
from typing import List, Dict, Any, Optional, cast

from .llm_client import LLMClient
import shared.database as db_utils
from . import parser_factory
from .prompts import (
    SCHEMA_EXTRACTION_SYSTEM_PROMPT,
    SCHEMA_EXTRACTION_USER_TEMPLATE,
)
from .utils import (
    log_event,
    decompose_stored_regex,
    apply_regex_matches,
    strip_html_to_text,
    convert_html_to_markdown_like,
)

logger = logging.getLogger(__name__)

def check_cached_parser(
    db, domain: str, fields: List[str], search_content: str, 
    source_type: str = "SEMANTIC", min_matches: int = 1, url_pattern: Optional[str] = None
) -> Dict[str, Any]:
    """Check for and apply cached parser. Supports multi-field merge strategy."""
    
    # 1. Try to find individual parsers for EACH field
    # We only assume success if we find a parser for ALL requested fields
    # (Or at least the major ones? For now, Strict: All or Nothing for structure consistency)
    
    parsers_map = {} # field -> parser_obj
    for field in fields:
        found = db_utils.find_cached_parser_by_fields(db, domain, [field], source_type, url_pattern=url_pattern, limit=1)
        if found:
            parsers_map[field] = found[0]
        else:
            # If any field is missing a parser, we might fallback to LLM.
            # OR we try to find a composite parser for the whole set (legacy support)
            break
            
    # If we found parsers for ALL fields, we execute them and Merge
    if len(parsers_map) == len(fields):
        # Execute each
        field_results = {} # field -> [val1, val2]
        min_len = 999999
        
        for field, p in parsers_map.items():
            pattern = p.generated_regex
            p_type = p.source_type
            flags = ""
            
            if p_type in ["REGEX", "HTML"] and "(?" in pattern:
                 patt, flags = decompose_stored_regex(cast(str, pattern))
                 matches = parser_factory.execute_parser("REGEX", patt, search_content, flags)
            elif p_type in ["REGEX", "HTML"]:
                 matches = parser_factory.execute_parser("REGEX", pattern, search_content)
            else:
                 matches = parser_factory.execute_parser(p_type, pattern, search_content)
                 
            # Extract basic values
            vals = [m["text"] for m in matches]
            field_results[field] = vals
            min_len = min(min_len, len(vals))
            
            db_utils.update_parser_usage(db, p.id)

        if min_len > 0 and min_len < 999999:
            # Zip Merge
            merged = []
            for i in range(min_len):
                item = {}
                for field in fields:
                    item[field] = field_results[field][i]
                
                # Text repr
                text_repr = " | ".join(f"{k}: {v}" for k,v in item.items())
                merged.append({
                    "text": text_repr,
                    "fields": item,
                    "source": "composite_cache",
                    "confidence": 0.9
                })
            
            logger.info(f"Composite Cache Hit: merged {min_len} items from {len(fields)} fields")
            return {
                "used_parser": None, # It's a composite, no single parser object to return
                "matches": merged,
                "used_cached": True
            }

    # 2. Legacy Fallback: Look for a single parser covering ALL fields
    parsers = db_utils.find_cached_parser_by_fields(db, domain, fields, source_type, url_pattern=url_pattern)

    for p in parsers:
        # Determine strategy from stored parser
        p_type = p.source_type
        pattern = p.generated_regex
        flags = ""
        
        # Regex patterns with inline flags
        if p_type in ["SEMANTIC", "REGEX", "HTML"] and "(?" in pattern:
            patt, flags = decompose_stored_regex(cast(str, pattern))
            matches = parser_factory.execute_parser("REGEX", patt, search_content, flags)
        elif p_type in ["SEMANTIC", "REGEX", "HTML"]:
            # Plain regex without flags prefix
            matches = parser_factory.execute_parser("REGEX", pattern, search_content)
        else:
            # CSS / JSONPATH
            matches = parser_factory.execute_parser(p_type, pattern, search_content)
        
        if matches and len(matches) >= min_matches:
            # Basic validation: ensure we got something
            try:
                db_utils.update_parser_usage(db, p.id)
                logger.info(f"Cache hit: parser_id={p.id}, domain={domain}, type={p_type}")
            except Exception:
                pass
            return {
                "used_parser": p,
                "matches": matches,
                "used_cached": True,
            }
        
        logger.info(f"Cache invalid: parser_id={p.id}, match_count={len(matches)}")
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
    """Schema extraction with semantic content + parser caching."""
    
    # 1. Content Preparation
    needs_media = any(f in ["image_url", "img", "photo", "src", "srcset"] or "image" in f.lower() or "img" in f.lower() for f in schema_fields)
    
    if needs_media and html_content:
        markdown_view = convert_html_to_markdown_like(html_content)
        content_for_llm = f"{markdown_view}\n\nSEMANTIC:\n{inner_text or ''}"
    elif inner_text and len(inner_text) > 200:
        if html_content:
             markdown_view = convert_html_to_markdown_like(html_content)
             content_for_llm = markdown_view if len(markdown_view) > 200 else inner_text
        else:
             content_for_llm = inner_text
    else:
        content_for_llm = inner_text or ""
    
    content_snippet = content_for_llm[:100000]
    
    # 2. LLM Extraction
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
        
        json_pattern = re.compile(r'(\{.*\})', re.DOTALL)
        json_match = json_pattern.search(response)
        if json_match:
            response = json_match.group(1)
        
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:].strip()
        if response.endswith("```"):
            response = response[:-3].strip()
        if "```json" in response:
            response = response.replace("```json", "").replace("```", "").strip()

        data = json.loads(response)
        log_event(task_id, "schema_llm_parsed", keys=list(data.keys()))
        
        items = data.get("items", [data] if any(f in data for f in schema_fields) else [])
        
        if not items:
            log_event(task_id, "schema_no_items")
            return []
        
        extracted_data = []
        for item in items:
            text_repr = " | ".join(f"{k}: {v}" for k, v in item.items() if v)
            extracted_data.append({
                "text": text_repr,
                "fields": item,
                "source": "schema_extraction",
                "confidence": 0.9
            })
        
        seen = set()
        deduped = []
        for item in extracted_data:
            f = item.get("fields", {})
            if not f:
                continue
            f_key = json.dumps(f, sort_keys=True)
            if f_key not in seen:
                seen.add(f_key)
                deduped.append(item)
        
        extracted_data = deduped
        log_event(task_id, "schema_extraction_success", count=len(extracted_data))
        
        # 3. Generate and Cache Parser
        if db and domain and extracted_data:
            logger.info(f"Attempting to cache parser for domain={domain}, fields={schema_fields}, items={len(extracted_data)}")
            try:
                # Use raw HTML or inner text depending on what's available
                raw_source = html_content if html_content else inner_text
                
                # IMPORTANT: If existing cache logic used 'SEMANTIC' for regex, we should consider that too.
                # But here we want to establish NEW parser types. 
                
                _cache_parser_from_extraction(
                    db, task_id, domain, schema_fields, 
                    raw_source, extracted_data, llm, url_pattern=url_pattern
                )
            except Exception as e:
                logger.warning(f"Failed to cache parser: {e}")
        else:
            logger.warning(f"Caching skipped: db={bool(db)}, domain={domain}, extracted_data_len={len(extracted_data)}")
        
        return extracted_data
        
    except json.JSONDecodeError as e:
        log_event(task_id, "schema_json_parse_error", error=str(e), response_preview=response[:200] if 'response' in locals() else "")
        return []
    except Exception as e:
        log_event(task_id, "schema_extraction_failed", error=str(e))
        return []


def _cache_parser_from_extraction(
    db, task_id: str, domain: str, fields: List[str],
    source_content: str, extracted_items: List[Dict], llm: LLMClient,
    url_pattern: Optional[str] = None
) -> None:
    """Generate parser (CSS/Regex/JSON) from successful extraction and cache it."""
    if len(extracted_items) < 2:
        log_event(task_id, "parser_cache_skip", reason="too_few_items")
        return
    
    examples = []
    for item in extracted_items[:5]:
        field_vals = item.get("fields", {})
        if not field_vals:
            continue
        examples.append(field_vals)
    
    if len(examples) < 2:
        log_event(task_id, "parser_cache_skip", reason="insufficient_examples")
        return
    
    try:
        target_desc = f"Extract fields: {', '.join(fields)}"
        
        # Use Factory to generate best parser
        result = parser_factory.generate_parser(
            content=source_content,
            examples=examples,
            target_desc=target_desc,
            llm=llm
        )
        
        if result.get("success"):
            
            # Handle Map return (Per-Field Parsers)
            if result.get("type") == "map" and result.get("parsers"):
                parsers_map = result["parsers"]
                source_type = result["source_type"]
                flags = result.get("flags", "")
                
                # Cache EACH field independently
                for field, pattern in parsers_map.items():
                    if source_type == "REGEX":
                        stored_regex = f"(?{flags}){pattern}" if flags else pattern
                    else:
                        stored_regex = pattern # CSS selector
                        
                    db_utils.create_parser_cache_by_fields(
                        db=db,
                        domain=domain,
                        fields=[field], # Single field
                        generated_regex=stored_regex,
                        source_type=source_type,
                        created_by_task_id=task_id,
                        test_matches_count=len(extracted_items),
                        confidence_score=int(0.9 * 100),
                        url_pattern=url_pattern,
                        sample_input=source_content[:2000],
                        sample_output=extracted_items[:10]
                    )
                
                log_event(task_id, "parser_cached_map", domain=domain, fields=list(parsers_map.keys()))
                
            else:
                # Legacy / Single Pattern
                pattern = result["pattern"]
                source_type = result["source_type"] # CSS, JSONPATH, REGEX
                flags = result.get("flags", "")
                
                # Store regex flags inline for DB compatibility
                if source_type == "REGEX":
                    stored_regex = f"(?{flags}){pattern}" if flags else pattern
                else:
                    stored_regex = pattern
                
                # Confidence estimation
                confidence = 0.9
                
                db_utils.create_parser_cache_by_fields(
                    db=db,
                    domain=domain,
                    fields=fields,
                    generated_regex=stored_regex,
                    source_type=source_type,
                    created_by_task_id=task_id,
                    test_matches_count=len(extracted_items),
                    confidence_score=int(confidence * 100),
                    url_pattern=url_pattern,
                    sample_input=source_content[:2000],
                    sample_output=extracted_items[:10]
                )
                log_event(task_id, "parser_cached", domain=domain, type=source_type, matches=len(extracted_items))
        else:
             # handle error
            logger.warning(f"Parser generation failed: {result.get('error')}")
            log_event(task_id, "parser_generation_failed", error=result.get("error"))
            
    except Exception as e:
        logger.warning(f"Parser caching exception: {e}")
        log_event(task_id, "parser_cache_error", error=str(e))


def run_field_extraction(
    task_id: str, keywords: List[str],
    inner_text: str, html_content: str, llm: LLMClient, db, domain: str,
    url_pattern: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Simple field extraction using regex generation with field-based caching."""
    search_content = html_content if html_content else inner_text
    
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
    
    all_matches = []
    
    for field in keywords:
        field_examples = [ex for ex in examples if field.lower() in ex.lower()][:3]
        if not field_examples:
            field_examples = [field]
        
        # Use parser factory for consistent parser generation
        result = parser_factory.generate_parser(
             content=search_content,
             examples=field_examples,
             target_desc=field,
             llm=llm
        )
        
        if result.get("success"):
            pattern = result["pattern"]
            flags = result.get("flags", "")
            source_type = result["source_type"]
            
            # Execute
            matches = parser_factory.execute_parser(source_type, pattern, search_content, flags)
            
            if matches:
                log_event(task_id, "field_parser_success", field=field, count=len(matches), type=source_type)
                # Convert to flat dicts
                all_matches.extend([{"text": m["text"], "field": field, "source": source_type} for m in matches])
                
                if db and domain:
                    try:
                        if source_type == "REGEX":
                            stored = f"(?{flags}){pattern}" if flags else pattern
                        else:
                            stored = pattern
                            
                        db_utils.create_parser_cache_by_fields(
                            db=db,
                            domain=domain,
                            fields=[field],
                            generated_regex=stored,
                            source_type=source_type,
                            created_by_task_id=task_id,
                            test_matches_count=len(matches),
                            confidence_score=85,
                            url_pattern=url_pattern,
                            sample_input=search_content[:2000],
                            sample_output=[{"text": m["text"]} for m in matches[:10]]
                        )
                    except Exception as cache_err:
                        logger.warning(f"Failed to cache field parser: {cache_err}")

    if all_matches:
        log_event(task_id, "field_extraction_success", count=len(all_matches))
        return [{"text": m["text"], "source": "field_extraction", "confidence": 0.85} for m in all_matches]
    
    return []

