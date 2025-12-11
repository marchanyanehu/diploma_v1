"""
Extraction Strategies Module

Provides multiple extraction approaches:
1. Combined Regex - Single regex with named groups for all fields
2. CSS Selectors - BeautifulSoup-based extraction (optional)
3. Direct LLM - Let LLM extract directly from small pages
4. Per-Field Regex - Current approach (fallback)

The key insight: Instead of generating separate regexes per field and then
trying to group them by position, generate ONE regex that captures a complete
record with all fields at once. Each match = one record. No grouping needed.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class ExtractionStrategy(Enum):
    DIRECT_LLM = "direct_llm"
    COMBINED_REGEX = "combined_regex"
    PER_FIELD_REGEX = "per_field_regex"


# ---------------------------------------------------------------------------
# Prompts for Combined Regex Generation
# ---------------------------------------------------------------------------

FIND_RECORD_CONTAINER_SYSTEM = """You analyze HTML structure to identify repeating record patterns.
Output ONLY valid JSON. No explanations."""

FIND_RECORD_CONTAINER_USER = """Analyze this HTML and find the repeating container element for records containing: {fields}

HTML (first part):
{html_sample}

Find the HTML element that wraps each individual record (article, div, li, tr, etc.)
Look for class names or attributes that identify the record container.

Output JSON:
{{
  "container_tag": "article|div|li|tr|etc",
  "container_selector": "CSS selector like article.news-item or div[data-item]",
  "sample_count": number of such containers found,
  "confidence": 0.0-1.0
}}"""

COMBINED_REGEX_SYSTEM = """You are an expert at generating combined regex patterns that extract multiple fields at once.
The regex should match a complete record and capture each field with a named group.
Output ONLY valid JSON. Escape backslashes properly for JSON (use \\\\ for a literal backslash in regex)."""

COMBINED_REGEX_USER = """Generate a regex to extract records with these fields: {fields}

Example record HTML:
<<<RECORD>>>
{record_html}
<<<END_RECORD>>>

Requirements:
1. Match the COMPLETE record container (article, div, li, etc.)
2. Use NAMED capture groups with UNDERSCORED names: (?P<field_name>...)
   - Use underscores instead of spaces: "brief description" → (?P<brief_description>...)
3. Use [^<]+? for text content, [^"]+ for attribute values
4. Use \\s* for whitespace tolerance (escape as \\\\s* in JSON)
5. The regex should work for ALL similar records on the page

Field name mapping (use these exact group names):
{field_mapping}

Field extraction hints:
{field_hints}

Output JSON (escape all backslashes for JSON):
{{
  "regex": "your pattern here",
  "flags": "s",
  "explanation": "brief explanation"
}}"""


def _extract_record_samples(html: str, max_samples: int = 3) -> Tuple[str, List[str]]:
    """
    Try to find repeating record patterns in HTML.
    Returns (container_pattern, list_of_sample_records).
    """
    # Common record container patterns
    container_patterns = [
        (r'<article[^>]*>.*?</article>', 'article'),
        (r'<li[^>]*class="[^"]*item[^"]*"[^>]*>.*?</li>', 'li.item'),
        (r'<div[^>]*class="[^"]*(?:card|item|product|listing|entry|result)[^"]*"[^>]*>.*?</div>\s*(?=<div|$)', 'div.card'),
        (r'<tr[^>]*>.*?</tr>', 'tr'),
    ]
    
    for pattern, name in container_patterns:
        matches = list(re.finditer(pattern, html, re.DOTALL | re.IGNORECASE))
        if len(matches) >= 3:  # Need at least 3 records to be confident
            samples = [m.group(0) for m in matches[:max_samples]]
            return pattern, samples
    
    return "", []


def _generate_field_hints(fields: List[str]) -> str:
    """Generate hints for common field types."""
    hints = []
    field_lower = [f.lower() for f in fields]
    
    if any('title' in f or 'name' in f for f in field_lower):
        hints.append("- title/name: Usually in h1-h6, a, or span with class containing 'title'")
    if any('price' in f or 'cost' in f for f in field_lower):
        hints.append("- price: Look for currency symbols (€,$,£) or class containing 'price'")
    if any('date' in f or 'time' in f for f in field_lower):
        hints.append("- date: Look for date patterns (DD-MM-YYYY, etc.) or class containing 'date'")
    if any('desc' in f for f in field_lower):
        hints.append("- description: Usually in p tags or div with class containing 'content', 'desc', 'summary'")
    if any('url' in f or 'link' in f for f in field_lower):
        hints.append("- url/link: Extract href attribute from a tags")
    
    return "\n".join(hints) if hints else "- Extract text content from appropriate HTML elements"


def extract_via_combined_regex(
    html: str,
    fields: List[str],
    llm,
    task_id: str = ""
) -> Dict[str, Any]:
    """
    Extract records using a single combined regex with named groups.
    
    This approach:
    1. Finds sample records in the HTML
    2. Asks LLM to generate ONE regex that captures all fields
    3. Each regex match = one complete record (no position grouping needed!)
    
    Returns:
        {
            "success": bool,
            "records": List[Dict],
            "regex_pattern": str,
            "match_count": int,
            "error": str (if failed)
        }
    """
    from shared.llm_client import LLMClient
    
    # Step 1: Find sample records
    container_pattern, samples = _extract_record_samples(html)
    
    if not samples:
        # Fallback: use first 10KB as sample
        samples = [html[:10000]]
        logger.info(f"[{task_id}] No clear record pattern found, using HTML prefix as sample")
    else:
        logger.info(f"[{task_id}] Found {len(samples)} sample records with pattern")
    
    # Step 2: Ask LLM to generate combined regex
    record_sample = samples[0][:5000]  # Limit sample size
    field_hints = _generate_field_hints(fields)
    
    # Create field name mapping (spaces → underscores)
    field_mapping = "\n".join(
        f'  - "{f}" → (?P<{f.replace(" ", "_")}>...)'
        for f in fields
    )
    
    messages = [
        {"role": "system", "content": COMBINED_REGEX_SYSTEM},
        {"role": "user", "content": COMBINED_REGEX_USER.format(
            fields=", ".join(fields),
            record_html=record_sample,
            field_hints=field_hints,
            field_mapping=field_mapping
        )}
    ]
    
    try:
        response = llm.chat(messages, temperature=0.1)
        response_text = response.strip()
        
        # Clean up response
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
        
        # Try to parse JSON, with fallback for escape issues
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # LLM sometimes returns regex with invalid escapes for JSON
            # Try to extract the regex pattern directly
            regex_match = re.search(r'"regex"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text)
            if regex_match:
                # Manually extract and unescape
                raw_pattern = regex_match.group(1)
                result = {"regex": raw_pattern, "flags": "s"}
            else:
                raise
        
        pattern = result.get("regex", "")
        flags_str = result.get("flags", "s")
        
        if not pattern:
            return {"success": False, "records": [], "error": "LLM returned empty pattern"}
        
        # Build regex flags
        flags = 0
        if 's' in flags_str.lower():
            flags |= re.DOTALL
        if 'i' in flags_str.lower():
            flags |= re.IGNORECASE
        if 'm' in flags_str.lower():
            flags |= re.MULTILINE
        
        # Step 3: Apply combined regex
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            logger.warning(f"[{task_id}] Invalid regex pattern: {e}")
            return {"success": False, "records": [], "error": f"Invalid regex: {e}"}
        
        records = []
        for match in compiled.finditer(html):
            record = {}
            # Extract named groups - try various name formats
            for field in fields:
                underscored = field.replace(" ", "_")
                nospace = field.replace(" ", "")
                # Try field name variations
                for group_name in [field, underscored, nospace, field.lower(), underscored.lower()]:
                    try:
                        value = match.group(group_name)
                        if value:
                            record[field] = value.strip()
                            break
                    except (IndexError, re.error):
                        continue
                
                if field not in record:
                    record[field] = None
            
            # Only add records with at least one non-None field
            if any(v is not None for v in record.values()):
                records.append(record)
        
        logger.info(f"[{task_id}] Combined regex extracted {len(records)} records")
        
        # Quality validation: check field completeness
        if records:
            # Calculate how many records have ALL fields non-null
            complete_records = sum(
                1 for r in records 
                if all(v is not None and v.strip() for v in r.values())
            )
            completeness_rate = complete_records / len(records)
            
            # Also check individual field fill rates
            field_fill_rates = {}
            for field in fields:
                filled = sum(1 for r in records if r.get(field) is not None and str(r.get(field, '')).strip())
                field_fill_rates[field] = filled / len(records)
            
            avg_fill_rate = sum(field_fill_rates.values()) / len(field_fill_rates) if field_fill_rates else 0
            
            logger.info(f"[{task_id}] Quality check: completeness={completeness_rate:.1%}, avg_fill={avg_fill_rate:.1%}, field_rates={field_fill_rates}")
            
            # If quality is poor, return as low-quality so caller can fallback
            if avg_fill_rate < 0.5 or completeness_rate < 0.3:
                logger.warning(f"[{task_id}] Combined regex quality too low, marking for fallback")
                return {
                    "success": False,
                    "records": records,  # Include records for debugging
                    "regex_pattern": pattern,
                    "match_count": len(records),
                    "error": f"Quality too low: completeness={completeness_rate:.1%}, avg_fill={avg_fill_rate:.1%}",
                    "quality_issue": True
                }
        
        return {
            "success": len(records) > 0,
            "records": records,
            "regex_pattern": pattern,
            "match_count": len(records),
            "error": None if records else "No matches found"
        }
        
    except json.JSONDecodeError as e:
        logger.warning(f"[{task_id}] Failed to parse LLM response as JSON: {e}")
        return {"success": False, "records": [], "error": f"JSON parse error: {e}"}
    except Exception as e:
        logger.warning(f"[{task_id}] Combined regex extraction failed: {e}")
        return {"success": False, "records": [], "error": str(e)}


def extract_via_direct_llm(
    html: str,
    fields: List[str],
    llm,
    task_id: str = "",
    max_html_size: int = 40000
) -> Dict[str, Any]:
    """
    For small pages, just let the LLM extract data directly.
    No regex generation at all - LLM reads HTML and returns JSON.
    
    This is the simplest possible approach but only works for small pages.
    """
    if len(html) > max_html_size:
        return {
            "success": False,
            "records": [],
            "error": f"HTML too large for direct extraction ({len(html)} > {max_html_size})"
        }
    
    prompt = f"""Extract all records from this HTML page.
Fields to extract: {', '.join(fields)}

HTML:
{html}

Return a JSON array of objects. Each object should have these fields: {', '.join(fields)}
If a field is not found for a record, use null.

Output ONLY the JSON array, no other text."""
    
    messages = [
        {"role": "system", "content": "You extract structured data from HTML. Output ONLY valid JSON arrays."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = llm.chat(messages, temperature=0.0)
        response_text = response.strip()
        
        # Clean up response
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
        
        records = json.loads(response_text)
        
        if not isinstance(records, list):
            records = [records]
        
        # Normalize field names
        normalized = []
        for record in records:
            norm_record = {}
            for field in fields:
                # Try to find the field with various capitalizations
                for key in record.keys():
                    if key.lower().replace("_", " ") == field.lower().replace("_", " "):
                        norm_record[field] = record[key]
                        break
                if field not in norm_record:
                    norm_record[field] = record.get(field)
            normalized.append(norm_record)
        
        logger.info(f"[{task_id}] Direct LLM extraction got {len(normalized)} records")
        
        return {
            "success": len(normalized) > 0,
            "records": normalized,
            "match_count": len(normalized),
            "error": None if normalized else "No records extracted"
        }
        
    except json.JSONDecodeError as e:
        logger.warning(f"[{task_id}] Failed to parse LLM extraction response: {e}")
        return {"success": False, "records": [], "error": f"JSON parse error: {e}"}
    except Exception as e:
        logger.warning(f"[{task_id}] Direct LLM extraction failed: {e}")
        return {"success": False, "records": [], "error": str(e)}


def select_extraction_strategy(
    html: str,
    fields: List[str],
    force_strategy: Optional[ExtractionStrategy] = None
) -> ExtractionStrategy:
    """
    Select the best extraction strategy based on content characteristics.
    """
    if force_strategy:
        return force_strategy
    
    html_size = len(html)
    
    # Very small pages: direct LLM extraction
    if html_size < 30000:
        return ExtractionStrategy.DIRECT_LLM
    
    # Default: combined regex (simpler than per-field)
    return ExtractionStrategy.COMBINED_REGEX


def unified_extract(
    html: str,
    fields: List[str],
    llm,
    task_id: str = "",
    strategy: Optional[ExtractionStrategy] = None
) -> Dict[str, Any]:
    """
    Unified extraction interface that selects and applies the best strategy.
    
    Returns:
        {
            "success": bool,
            "records": List[Dict],
            "strategy_used": str,
            "match_count": int,
            "error": str (if all strategies failed)
        }
    """
    selected_strategy = select_extraction_strategy(html, fields, strategy)
    logger.info(f"[{task_id}] Selected extraction strategy: {selected_strategy.value}")
    
    # Try selected strategy first
    if selected_strategy == ExtractionStrategy.DIRECT_LLM:
        result = extract_via_direct_llm(html, fields, llm, task_id)
        if result["success"]:
            result["strategy_used"] = "direct_llm"
            return result
        # Fallback to combined regex
        logger.info(f"[{task_id}] Direct LLM failed, falling back to combined regex")
        selected_strategy = ExtractionStrategy.COMBINED_REGEX
    
    if selected_strategy == ExtractionStrategy.COMBINED_REGEX:
        result = extract_via_combined_regex(html, fields, llm, task_id)
        if result["success"]:
            result["strategy_used"] = "combined_regex"
            return result
        # Fallback to per-field (current approach)
        logger.info(f"[{task_id}] Combined regex failed, falling back to per-field regex")
    
    # Final fallback: signal to use existing per-field approach
    return {
        "success": False,
        "records": [],
        "strategy_used": "fallback_to_per_field",
        "match_count": 0,
        "error": "New strategies failed, use existing per-field approach"
    }
