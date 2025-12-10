
import re
import logging
from typing import List, Dict, Any

from .utils import extract_snippet, extract_micro_snippet

logger = logging.getLogger(__name__)

def extract_attribute_from_html_by_text(html_content: str, text_examples: List[str], attribute: str) -> List[str]:
    """Extract specific attribute values from HTML by finding elements that contain the given text examples."""
    values = []
    seen_values: set = set()
    
    # Normalize attribute name
    attr = attribute.lower()
    
    # Heuristic regex: Find opening tag with the attribute, capture value and some following content
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

def find_text_in_raw_content(raw_content: str, text_examples: List[str], max_candidates: int = 20) -> List[Dict[str, Any]]:
    """Step 3: Find text examples in raw content (no LLM, pure string search)."""
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
                
                snippet = extract_snippet(raw_content, idx, len(search_term))
                micro = extract_micro_snippet(raw_content, idx, len(search_term))
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

def extract_field_examples(example_texts: List[str], field: str) -> List[str]:
    """Extract field-specific examples from structured examples."""
    field_examples = []
    field_lower = field.lower().rstrip('s')  # Remove trailing 's' for flexible matching
    
    for ex in example_texts:
        found = False
        
        # Try parsing as dict (JSON or Python repr)
        try:
            stripped = ex.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                import ast
                # Use literal_eval for safety (handles python dict syntax with single quotes)
                data = ast.literal_eval(stripped)
                if isinstance(data, dict):
                    # Try exact match, lower match, or partial match
                    val = data.get(field) or data.get(field_lower)
                    if not val:
                        # Try finding key case-insensitively
                        for k, v in data.items():
                            if k.lower() == field_lower:
                                val = v
                                break
                    
                    if val:
                        field_examples.append(str(val))
                        found = True
                        continue
        except Exception:
            pass

        if found:
            continue

        # Try regex extraction (handles {"id": 123, ...} format if eval failed)
        # Updated to handle single or double quotes
        json_patterns = [
            rf'["\']{field_lower}["\']\s*:\s*["\']([^"\']*)["\']',  # String value: "field": "value" or 'field': 'value'
            rf'["\']{field_lower}["\']\s*:\s*(\d+)',       # Number value: "field": 123
            rf'["\']{field}["\']\s*:\s*["\']([^"\']*)["\']',         # Exact field name string
            rf'["\']{field}["\']\s*:\s*(\d+)',             # Exact field name number
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, ex, re.IGNORECASE)
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
        
        # REMOVED: Aggressive heuristic that assumed first line = entity name
        # This caused job_title to be extracted as company name when format was unclear
    
    return list(dict.fromkeys(field_examples))[:3]  # Dedupe and limit

def prepare_search_content(inner_text: str, raw_content: str) -> Dict[str, str]:
    """Prepare content sources for extraction."""
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
