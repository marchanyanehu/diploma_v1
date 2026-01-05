
import logging
from typing import Any, Dict, List, Optional, Union
import json
import re

try:
    from parsel import Selector
except ImportError:
    Selector = None

logger = logging.getLogger(__name__)

CSS_GENERATION_SYSTEM_PROMPT = """You are a CSS Selector expert. Your goal is to generate a SINGLE, ROBUST CSS selector (compatible with parsel/Scrapy) to extract specific elements from HTML.

Rules:
1. Return ONLY a JSON object: {"selector": "div.job > a::attr(href)", "attribute": "href", "explanation": "..."}
2. Use specific attributes (class, id, data-testid) but avoid random/generated strings (e.g. css-1a2b3c).
3. If extracting text, use `::text`. If extracting value, use `::attr(value)`.
4. Prefer structural robustness over shortness.
"""

CSS_USER_TEMPLATE = """TARGET: {target_desc}

EXAMPLES (The selector MUST extract these exact values):
{examples_json}

HTML SNIPPET:
{snippet}

Generate a CSS selector to extract the target values."""


def generate_css_selector(
    html_content: str,
    examples: List[Union[str, Dict]],
    target_desc: str,
    llm: Any,
    max_retries: int = 2,
    expected_count: Optional[int] = None
) -> Dict[str, Any]:
    
    if not Selector:
        return {"success": False, "error": "parsel not installed"}

    if not examples:
        return {"success": False, "error": "No examples provided"}

    # Detect multi-field mode
    is_multi_field = isinstance(examples[0], dict) and len(examples[0]) > 1
    
    if is_multi_field:
        # Multi-field strategy: Generate selector for EACH field
        first_ex = examples[0]
        components = {}
        
        for key in first_ex.keys():
            # Extract examples just for this field
            field_examples = [ex.get(key) for ex in examples if ex.get(key)]
            if not field_examples:
                continue
                
            field_target = f"{target_desc} - {key}"
            
            # Recursive call for single field
            result = generate_css_selector(
                html_content, 
                field_examples, 
                field_target, 
                llm, 
                max_retries=max_retries, 
                expected_count=expected_count
            )
            
            if result.get("success"):
                components[key] = result["selector"]
            else:
                return {"success": False, "error": f"Failed to generate CSS for field '{key}': {result.get('error')}"}
        
        return {
            "success": True, 
            "selectors": components, # {field: selector}
            "type": "map"
        }

    # --- Single Field Strategy ---
    
    # Prepare flat examples
    flat_examples = []
    for ex in examples:
        if isinstance(ex, dict):
             # Take the first available value
             flat_examples.extend([str(v) for v in ex.values() if v])
        else:
             flat_examples.append(str(ex))
            
    # Locate snippet
    snippet = _get_snippet(html_content, flat_examples)
    
    prompt = CSS_USER_TEMPLATE.format(
        target_desc=target_desc,
        examples_json=json.dumps(flat_examples[:5], ensure_ascii=False),
        snippet=snippet
    )
    
    attempts = []
    
    for i in range(max_retries + 1):
        try:
            response = llm.chat([
                {"role": "system", "content": CSS_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ], temperature=0.2)
            
            parsed = _parse_json(response)
            selector = parsed.get("selector")
            
            if not selector:
                attempts.append({"error": "No selector in JSON"})
                continue
                
            # Validate
            validation = _validate_selector(html_content, selector, flat_examples, expected_count=expected_count)
            attempts.append({"selector": selector, "validation": validation})
            
            if validation["success"]:
                return {
                    "success": True,
                    "selector": selector,
                    "attribute": parsed.get("attribute", ""),
                    "metadata": {"attempts": attempts}
                }
            
            # If failed, Refine
            prompt += f"\n\nPrevious attempt {selector} failed: {validation['issue']}. Try again."
            
        except Exception as e:
            attempts.append({"error": str(e)})

    return {"success": False, "error": "Max retries exceeded", "attempts": attempts}

def _validate_selector(
    html: str, 
    selector: str, 
    examples: List[str],
    expected_count: Optional[int] = None
) -> Dict[str, Any]:
    try:
        sel = Selector(text=html)
        extracted = sel.css(selector).getall()
        # Clean extracted
        extracted = [e.strip() for e in extracted if e and e.strip()]
        
        extracted_set = set(extracted)
        
        # 1. Count Check (Strict)
        if expected_count is not None:
            if len(extracted) != expected_count:
                return {
                    "success": False, 
                    "issue": f"Count mismatch: expected {expected_count} items, found {len(extracted)}"
                }

        # 2. Example Coverage Check
        found_count = 0
        for ex in examples:
            if ex in extracted_set:
                found_count += 1
            else:
                # partial match check
                if any(ex in val for val in extracted):
                    found_count += 1
                    
        if found_count == 0:
            return {"success": False, "issue": "No examples found"}
        
        if found_count / len(examples) < 0.5:
            # If we don't have expected_count to enforce, we rely on coverage
            return {"success": False, "issue": f"Only found {found_count}/{len(examples)} examples"}
            
        return {"success": True, "count": len(extracted)}
        
    except Exception as e:
        return {"success": False, "issue": str(e)}

def _get_snippet(html: str, examples: List[str]) -> str:
    # return window around first example
    if not examples:
        return html[:5000]
    
    idx = html.find(examples[0])
    if idx == -1:
        return html[:5000]
        
    start = max(0, idx - 1000)
    end = min(len(html), idx + 4000)
    return html[start:end]

def _parse_json(text: str) -> Dict:
    try:
        return json.loads(text)
    except:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {}
