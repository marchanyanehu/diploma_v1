
import logging
import json
import re
from typing import List, Dict, Any, Optional, cast
from urllib.parse import urlparse

from shared.llm_client import LLMClient
from services.api import db_utils
from . import regex_generation
from .prompts import (
    SCHEMA_EXTRACTION_SYSTEM_PROMPT,
    SCHEMA_EXTRACTION_USER_TEMPLATE,
    ATTRIBUTE_EXTRACTION_USER_TEMPLATE
)
from .utils import (
    log_event, decompose_stored_regex, apply_regex_matches, 
    strip_html_to_text, looks_like_html, extract_snippet
)
from .llm_ops import (
    find_structured_examples_via_llm, find_matching_text_via_llm,
    select_best_candidate_via_llm, generate_field_regex,
    extract_attribute_via_llm, filter_values_via_llm
)
from .content_ops import (
    find_text_in_raw_content, extract_field_examples,
    extract_attribute_from_html_by_text
)
from .snippet_extractor import extract_snippet_around_example

logger = logging.getLogger(__name__)

def check_cached_parser(db, domain: str, keywords: List[str], search_content: str, source_type: str = None) -> Dict[str, Any]:
    """Check for and apply cached parser."""
    parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
    
    for p in parsers:
        # Filter by source_type if specified
        if source_type and p.source_type != source_type:
            continue
            
        patt, fl = decompose_stored_regex(cast(str, p.generated_regex))
        matches = apply_regex_matches(patt, fl, search_content)
        if matches:
            return {
                "used_parser": p,
                "matches": matches,
                "used_cached": True,
            }
    
    return {"used_parser": None, "matches": [], "used_cached": False}

def step2_find_matching_text(
    task_id: str, inner_text: str, intent: Dict, 
    is_multi_field: bool, is_attribute_target: bool, keywords: List[str], llm: LLMClient
) -> List[str]:
    """Step 2: Find raw text that matches the keyword via LLM (from inner_text)."""
    target = intent.get("target", "") or "target data"
    matched_texts = []
    
    if is_multi_field:
        log_event(task_id, "step_2_llm_multi_field_matching")
        matched_texts = find_structured_examples_via_llm(inner_text, target, keywords, llm)
    else:
        # Use LLM to find matching text in inner_text
        log_event(task_id, "step_2_llm_text_matching", is_attribute_target=is_attribute_target)
        matched_texts = find_matching_text_via_llm(inner_text, target, llm, is_attribute_target=is_attribute_target)
    
    # Last resort: use keywords as fallback
    if not matched_texts:
        matched_texts = keywords[:3]
    
    return matched_texts

def steps3_4_find_and_select_snippet(
    task_id: str, raw_content: str, matched_texts: List[str], 
    intent: Dict, llm: LLMClient
) -> Dict[str, str]:
    """Steps 3-4: Find text in raw content (no LLM), then select best candidate via LLM."""
    # Step 3: Find text in raw content (no LLM, pure string search)
    log_event(task_id, "step_3_find_in_raw_content", text_count=len(matched_texts))
    candidates = find_text_in_raw_content(raw_content, matched_texts)
    log_event(task_id, "step_3_candidates_found", candidate_count=len(candidates))
    
    best_snippet = ""
    micro_snippets = ""
    
    if candidates:
        # Step 4: Provide snippets to LLM, select best candidate
        log_event(task_id, "step_4_select_best_candidate", candidate_count=len(candidates))
        best = select_best_candidate_via_llm(candidates, intent, llm)
        best_snippet = best.get("snippet", "")
        
        # Combine all micro-snippets for focused regex generation
        micros = [c.get("micro_snippet", "") for c in candidates if c.get("micro_snippet")]
        micro_snippets = "\n---\n".join(micros[:5])
    
    # Fallback: extract snippet around first matched text
    if not best_snippet:
        snip = extract_snippet_around_example(raw_content, matched_texts[0] if matched_texts else "", max_chars=4000)
        best_snippet = cast(str, snip.get("snippet", ""))
    
    return {"snippet": best_snippet, "micro_snippets": micro_snippets}

def run_multi_field_extraction(
    task_id: str, keywords: List[str], example_texts: List[str],
    search_content: str, snippet_to_use: str, llm: LLMClient
) -> List[Dict[str, Any]]:
    """Generate separate regex for each field and combine results."""
    log_event(task_id, "multi_field_extraction", fields=keywords)
    field_results = {}
    
    for field in keywords:
        field_examples = extract_field_examples(example_texts, field)
        if not field_examples:
            continue
        
        log_event(task_id, "field_examples", field=field, examples=field_examples)
        
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
            matches = apply_regex_matches(pattern, flags, search_content)
            if matches:
                unique = list(dict.fromkeys(matches))
                field_results[field] = unique
                log_event(task_id, "field_regex_success", field=field, match_count=len(unique))
            else:
                log_event(task_id, "field_regex_no_matches", field=field, pattern=pattern)
        else:
            log_event(task_id, "field_regex_failed", field=field, error=gen.get("error"))
    
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
        log_event(task_id, "multi_field_success", record_count=len(extracted_data))
    
    return extracted_data

def run_schema_extraction_with_cache(
    task_id: str, url: str, schema_fields: List[str], inner_text: str,
    html_content: str, llm: LLMClient, db, domain: str
) -> tuple[List[Dict[str, Any]], bool]:
    """Extract data with LLM, then generate and cache regexes for reuse."""
    log_event(task_id, "schema_extraction_start", fields=schema_fields)
    
    # Check for cached schema regex first
    cached_parsers = db_utils.find_cached_parser(db, domain, keywords=schema_fields) if db else []
    
    for parser in cached_parsers:
        try:
            stored_regex = cast(str, parser.generated_regex)
            pattern, flags = decompose_stored_regex(stored_regex)
            
            # Unwrap potentially nested flags
            while pattern.startswith("(?"):
                pattern, _ = decompose_stored_regex(pattern)

            if pattern.startswith("SCHEMA:"):
                json_str = pattern[7:]
                try:
                    schema_data = json.loads(json_str)
                    field_regexes = schema_data.get("field_regexes", {})
                    
                    # Apply regexes
                    field_matches = {}
                    match_counts = []
                    
                    for field, regex_info in field_regexes.items():
                        r_pattern = regex_info.get("regex")
                        r_flags = regex_info.get("flags", "s")
                        matches = apply_regex_matches(r_pattern, r_flags, html_content)
                        
                        # Clean matches
                        cleaned = []
                        for m in matches:
                            if looks_like_html(m):
                                cleaned.append(strip_html_to_text(m))
                            else:
                                cleaned.append(m)
                        
                        field_matches[field] = cleaned
                        match_counts.append(len(cleaned))
                    
                    # Check if counts align (simple heuristic for association)
                    if match_counts and all(c == match_counts[0] for c in match_counts) and match_counts[0] > 0:
                        count = match_counts[0]
                        extracted = []
                        for i in range(count):
                            record = {}
                            for field in field_regexes:
                                record[field] = field_matches[field][i]
                            
                            text_repr = " | ".join(f"{k}: {v}" for k, v in record.items() if v)
                            extracted.append({
                                "text": text_repr,
                                "fields": record,
                                "source": "cached_schema_regex",
                                "confidence": 1.0
                            })
                        
                        log_event(task_id, "schema_cache_hit", parser_id=parser.id, count=len(extracted))
                        return extracted, True
                    else:
                        log_event(task_id, "schema_cache_mismatch_counts", counts=match_counts)
                        
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.warning(f"Failed to apply cached schema parser: {e}")
    
    log_event(task_id, "schema_cache_miss", generating_new=True)
    
    # No cache hit - use LLM extraction
    fields_list = ", ".join(schema_fields)
    prompt = SCHEMA_EXTRACTION_USER_TEMPLATE.format(
        fields_list=fields_list,
        content_snippet=inner_text[:15000]
    )

    messages = [
        {
            "role": "system",
            "content": SCHEMA_EXTRACTION_SYSTEM_PROMPT,
        },
        {"role": "user", "content": prompt},
    ]

    raw_response = llm.chat(
        messages,
        temperature=0.1,
        extra_params={"response_format": {"type": "json_object"}},
    )
    log_event(task_id, "schema_llm_response", response=raw_response[:500])

    # Parse the JSON response
    parsed_data = None
    try:
        parsed_data = json.loads(raw_response)
    except json.JSONDecodeError:
        array_match = re.search(r"\[[\s\S]*\]", raw_response)
        if array_match:
            try:
                parsed_data = json.loads(array_match.group(0))
            except Exception:
                parsed_data = None
        if parsed_data is None:
            obj_match = re.search(r"\{[\s\S]*\}", raw_response)
            if obj_match:
                try:
                    parsed_data = json.loads(obj_match.group(0))
                except Exception:
                    parsed_data = None

    if parsed_data is None:
        log_event(task_id, "schema_extraction_failed", error="Could not parse JSON response")
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

    log_event(task_id, "schema_records_found", count=len(records))

    # Build result records from LLM extraction
    extracted_data = []
    field_examples = {field: [] for field in schema_fields}

    image_urls_from_page: List[str] = []
    if "image_url" in schema_fields and html_content:
        img_pattern = r'<img[^>]+(?:data-src|src)\s*=\s*"([^"]+)"'
        image_urls_from_page = re.findall(img_pattern, html_content, flags=re.IGNORECASE)
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
        
        for field in schema_fields:
            if field in record and record[field]:
                field_examples[field].append(str(record[field]))
        
        for field in schema_fields:
            if 'url' in field.lower() and (not record.get(field) or record.get(field) == ""):
                apply_pattern = r'href=["\']([^"\']*(?:apply|career|job)[^"\']*)["\']'
                apply_matches = re.findall(apply_pattern, html_content, re.IGNORECASE)
                if apply_matches:
                    full_urls = [u for u in apply_matches if u.startswith('http')]
                    record[field] = full_urls[0] if full_urls else apply_matches[0]

        if "image_url" in schema_fields and record.get("image_url"):
            field_examples["image_url"].append(str(record["image_url"]))
        
        record_fields = {}
        for field in schema_fields:
            if field in record and record[field]:
                record_fields[field] = str(record[field])
        
        if record_fields:
            text_repr = " | ".join(f"{k}: {v}" for k, v in record_fields.items() if v)
            extracted_data.append({
                "text": text_repr,
                "fields": record_fields,
                "source": "schema_llm",
                "confidence": 0.95
            })

    if "image_url" in schema_fields and not field_examples.get("image_url") and image_urls_from_page:
        field_examples["image_url"].extend(image_urls_from_page[:5])
    
    if not extracted_data:
        log_event(task_id, "schema_extraction_failed", error="no_records_from_llm")
        return [], False
    
    log_event(task_id, "schema_llm_extraction_complete", count=len(extracted_data))
        
    # Generate regex patterns for caching
    field_regexes = {}
    if len(records) >= 1:
        log_event(task_id, "schema_generating_regex_for_cache", field_count=len(schema_fields))
        for field, examples in field_examples.items():
            if examples:
                regex_result = generate_field_regex(field, examples, html_content, llm)
                if regex_result and regex_result.get("regex"):
                    field_regexes[field] = regex_result
                    log_event(task_id, "schema_field_regex_generated", field=field)

    # Validate regexes
    validated_field_regexes = {}
    if field_regexes:
        log_event(task_id, "schema_regex_validation_start", field_count=len(field_regexes))
        
        for field, regex_info in field_regexes.items():
            pattern = regex_info.get("regex", "")
            flags = regex_info.get("flags", "s")
            expected_values = field_examples.get(field, [])
            
            if not pattern or not expected_values:
                continue
            
            try:
                regex_matches = apply_regex_matches(pattern, flags, html_content)
                if regex_matches:
                    cleaned_matches = []
                    for m in regex_matches:
                        clean = strip_html_to_text(m) if looks_like_html(m) else m
                        if clean:
                            normalized = ' '.join(clean.split())
                            cleaned_matches.append(normalized)
                    
                    matched_count = 0
                    for expected in expected_values:
                        expected_normalized = ' '.join(expected.split())
                        for m in cleaned_matches:
                            if expected_normalized == m:
                                matched_count += 1
                                break
                            if expected_normalized in m or m in expected_normalized:
                                matched_count += 1
                                break
                            if len(expected_normalized) > 50 and len(m) > 50:
                                if expected_normalized[:50] == m[:50]:
                                    matched_count += 1
                                    break
                    
                    match_rate = matched_count / len(expected_values) if expected_values else 0
                    log_event(task_id, "schema_field_regex_validation", 
                              field=field, 
                              expected_count=len(expected_values),
                              regex_match_count=len(cleaned_matches),
                              validated_count=matched_count,
                              match_rate=round(match_rate, 2))
                    
                    if match_rate >= 0.6:
                        validated_field_regexes[field] = regex_info
                        log_event(task_id, "schema_field_regex_validated", field=field)
                    else:
                        log_event(task_id, "schema_field_regex_rejected", 
                                  field=field, reason="low_match_rate", match_rate=round(match_rate, 2),
                                  regex_pattern=pattern[:100])
                else:
                    log_event(task_id, "schema_field_regex_rejected", 
                              field=field, reason="no_matches", regex_pattern=pattern[:100])
            except Exception as e:
                log_event(task_id, "schema_field_regex_validation_error", field=field, error=str(e), regex_pattern=pattern[:100] if pattern else "none")

    # Identify fields that failed regex generation or validation
    failed_fields = [f for f in schema_fields if f in field_examples and field_examples[f] and f not in validated_field_regexes]
    
    # Retry failed fields using single-field extraction approach
    if failed_fields and db:
        log_event(task_id, "schema_regex_retry_start", failed_fields=failed_fields)
        
        for field in failed_fields:
            examples = field_examples.get(field, [])
            if not examples:
                continue
            
            try:
                field_intent = {
                    "target": field,
                    "keywords": [field] + [ex[:30] for ex in examples[:2]],
                }
                
                snippets = []
                for ex in examples[:3]:
                    if ex and ex in html_content:
                        idx = html_content.find(ex)
                        if idx != -1:
                            snippets.append(extract_snippet(html_content, idx, len(ex), context=300))
                
                snippet_to_use = "\n---\n".join(snippets[:3]) if snippets else html_content[:4000]
                best_snippet = html_content[:4000]
                
                single_result = run_single_field_extraction(
                    task_id=f"{task_id}_retry_{field}",
                    url=url,
                    intent=field_intent,
                    example_texts=examples[:5],
                    search_content=html_content,
                    best_snippet=best_snippet,
                    snippet_to_use=snippet_to_use,
                    llm=llm,
                    db=db
                )
                
                if single_result:
                    log_event(task_id, "schema_field_retry_success", field=field, match_count=len(single_result))
                else:
                    log_event(task_id, "schema_field_retry_failed", field=field)
                    
            except Exception as e:
                log_event(task_id, "schema_field_retry_error", field=field, error=str(e))

    # Cache only validated regexes
    if validated_field_regexes:
        combined_pattern = json.dumps({"schema_fields": schema_fields, "field_regexes": validated_field_regexes})
        try:
            db_utils.record_new_parser(
                db,
                task_id=task_id,
                url=url,
                intent={"keywords": schema_fields, "schema_fields": schema_fields},
                pattern=f"(?s:SCHEMA:{combined_pattern})",
                flags="s",
                matches_count=len(extracted_data),
                source_type="SCHEMA",
                sample_input=html_content[:2000],
                sample_output=[{"text": d["text"]} for d in extracted_data[:5]],
            )
            log_event(task_id, "schema_regex_cached", 
                      fields=list(validated_field_regexes.keys()),
                      validated_count=len(validated_field_regexes),
                      total_generated=len(field_regexes))
        except Exception as e:
            logger.warning(f"Failed to cache schema regex: {e}")
    else:
        log_event(task_id, "schema_regex_not_cached", reason="no_validated_regexes")

    log_event(task_id, "schema_extraction_success", record_count=len(extracted_data))
    return extracted_data, False

def run_schema_extraction(
    task_id: str, schema_fields: List[str], inner_text: str, html_content: str, llm: LLMClient
) -> List[Dict[str, Any]]:
    """Wrapper for backwards compatibility."""
    result, _ = run_schema_extraction_with_cache(
        task_id, "", schema_fields, inner_text, html_content, llm, None, ""
    )
    return result

def run_attribute_extraction(
    task_id: str, url: str, intent: Dict, text_examples: List[str],
    html_content: str, llm: LLMClient, db
) -> List[Dict[str, Any]]:
    """Extract attributes from HTML using unified regex approach with caching."""
    target = intent.get("target", "") or "target data"
    attribute = intent.get("target_attribute", "") or "href"
    domain = urlparse(url).netloc
    
    log_event(task_id, "attribute_extraction_start", attribute=attribute, text_examples=text_examples[:3])
    
    # Step 1: Check for cached ATTRIBUTE parser first
    cache_result = check_cached_parser(db, domain, intent.get("keywords", []), html_content, source_type="ATTRIBUTE")
    if cache_result["used_cached"] and cache_result["matches"]:
        log_event(task_id, "attribute_using_cached_parser", parser_id=cache_result["used_parser"].id, match_count=len(cache_result["matches"]))
        db_utils.update_parser_usage(db, cache_result["used_parser"].id)
        return [{"text": v, "source": "cached_attribute_regex", "confidence": 1.0} for v in cache_result["matches"]]
    
    # Step 2: Generate STRUCTURAL regex for attribute extraction via LLM
    log_event(task_id, "attribute_generating_regex")
    
    snippets = []
    for ex in text_examples[:5]:
        idx = html_content.lower().find(ex.lower())
        if idx != -1:
            snippet = extract_snippet(html_content, idx, len(ex), context=500)
            snippets.append(snippet)
    
    if not snippets:
        snippets = [html_content[:15000]]
    
    combined_snippet = "\n---\n".join(snippets[:3])[:15000]
    
    regex_prompt = ATTRIBUTE_EXTRACTION_USER_TEMPLATE.format(
        attribute=attribute,
        target=target,
        text_examples=text_examples[:3],
        combined_snippet=combined_snippet
    )
    
    pattern = None
    flags = "is"
    
    try:
        resp = llm.generate_text(regex_prompt, extra_params={"response_format": {"type": "json_object"}})
        data = json.loads(resp)
        pattern = data.get("regex")
        flags = data.get("flags", "is")
        log_event(task_id, "attribute_regex_generated", pattern=pattern[:100] if pattern else None)
        
        if pattern:
            for ex in text_examples:
                if ex and len(ex) > 5 and re.escape(ex) in pattern:
                    log_event(task_id, "attribute_regex_rejected_content_bound", pattern=pattern)
                    pattern = None
                    break
                    
    except Exception as e:
        log_event(task_id, "attribute_regex_generation_failed", error=str(e))
    
    extracted_values = []
    used_pattern = None
    
    # Step 3: Try LLM-generated STRUCTURAL regex first
    if pattern:
        matches = apply_regex_matches(pattern, flags, html_content)
        if matches:
            extracted_values = matches
            used_pattern = pattern
            log_event(task_id, "attribute_regex_success", match_count=len(matches))
    
    # Step 4: Fallback to simple heuristic regex
    if not extracted_values:
        log_event(task_id, "attribute_fallback_to_heuristic")
        extracted_values = extract_attribute_from_html_by_text(html_content, text_examples, attribute)
        if extracted_values:
            log_event(task_id, "attribute_heuristic_success", match_count=len(extracted_values))
    
    # Step 5: Final fallback to LLM direct extraction
    if not extracted_values:
        log_event(task_id, "attribute_fallback_to_llm_direct")
        extracted_values = extract_attribute_via_llm(html_content, text_examples, target, attribute, llm)
    
    extracted_data = []
    if extracted_values:
        filtered_values = filter_values_via_llm(extracted_values, target, llm)
        extracted_data = [{"text": v, "source": "attribute_extraction", "confidence": 0.9} for v in filtered_values]
        
        if used_pattern and len(filtered_values) > 0:
            try:
                db_utils.record_new_parser(
                    db,
                    task_id=task_id,
                    url=url,
                    intent=intent,
                    pattern=f"(?{flags}:{used_pattern})",
                    flags=flags,
                    matches_count=len(filtered_values),
                    source_type="ATTRIBUTE",
                    sample_input=html_content[:2000],
                    sample_output=[{"text": v} for v in filtered_values[:5]]
                )
                log_event(task_id, "attribute_parser_cached")
            except Exception as e:
                logger.warning(f"Failed to cache attribute parser: {e}")
    else:
        log_event(task_id, "attribute_extraction_failed_all_methods")
    
    return extracted_data

def run_single_field_extraction(
    task_id: str, url: str, intent: Dict, example_texts: List[str],
    search_content: str, best_snippet: str, snippet_to_use: str,
    llm: LLMClient, db
) -> List[Dict[str, Any]]:
    """Run the iterative regex generation pipeline for a single field."""
    gen_result = regex_generation.iterative_regex_generation(
        source=search_content,
        examples=example_texts,
        target_desc=intent.get("target", "target data"),
        llm=llm,
        max_iterations=3,
        snippet=snippet_to_use
    )
    
    extracted_data = []
    if gen_result.get("success"):
        final_pattern = gen_result.get("final_pattern")
        final_flags = gen_result.get("final_flags", "s")
        
        matches = apply_regex_matches(final_pattern, final_flags, search_content)
        if matches:
            unique_matches = list(dict.fromkeys(matches))
            extracted_data = [{"text": m, "source": "generated_regex", "confidence": 0.9} for m in unique_matches]
            
            try:
                db_utils.record_new_parser(
                    db,
                    task_id=task_id,
                    url=url,
                    intent=intent,
                    pattern=f"(?{final_flags}:{final_pattern})",
                    flags=final_flags,
                    matches_count=len(unique_matches),
                    source_type="CONTENT",
                    sample_input=best_snippet,
                    sample_output=[{"text": m} for m in unique_matches[:5]]
                )
                log_event(task_id, "parser_cached")
            except Exception as e:
                logger.warning(f"Failed to cache parser: {e}")
        else:
            log_event(task_id, "generated_regex_no_matches_on_full_content")
    else:
        log_event(task_id, "regex_generation_failed", error=gen_result.get("error"))
        
    return extracted_data
