
import logging
from typing import Any, Dict, List, Optional, Union
import json
import re

try:
    from jsonpath_ng import parse as parse_path
except ImportError:
    parse_path = None

logger = logging.getLogger(__name__)

JSON_GENERATION_SYSTEM_PROMPT = """You are a JSONPath expert. Your goal is to generate a SINGLE, ROBUST JSONPath expression to extract specific data from JSON.

Rules:
1. Return ONLY a JSON object: {"jsonpath": "$.items[*].url", "explanation": "..."}
2. Use wildcard `[*]` for arrays.
3. Handle nested structures carefully.
"""

JSON_USER_TEMPLATE = """TARGET: {target_desc}

EXAMPLES (The path MUST extract these values):
{examples_json}

JSON STRUCTURE SNIPPET:
{snippet}

Generate a JSONPath expression to extract the target values."""

def generate_json_path(
    json_content: str,
    examples: List[Union[str, Dict]],
    target_desc: str,
    llm: Any,
    max_retries: int = 2
) -> Dict[str, Any]:
    
    if not parse_path:
        return {"success": False, "error": "jsonpath-ng not installed"}

    # Prepare examples
    flat_examples = []
    for ex in examples:
        if isinstance(ex, dict):
            flat_examples.extend([str(v) for v in ex.values() if v])
        else:
            flat_examples.append(str(ex))
            
    # Truncate content for snippet (simple head for JSON usually works for structure)
    snippet = json_content[:5000]
    
    prompt = JSON_USER_TEMPLATE.format(
        target_desc=target_desc,
        examples_json=json.dumps(flat_examples[:5], ensure_ascii=False),
        snippet=snippet
    )
    
    attempts = []
    
    for i in range(max_retries + 1):
        try:
            response = llm.chat([
                {"role": "system", "content": JSON_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ], temperature=0.2)
            
            parsed = _parse_json(response)
            path = parsed.get("jsonpath")
            
            if not path:
                raise ValueError("No jsonpath returned")
                
            # Validate
            validation = _validate_path(json_content, path, flat_examples)
            attempts.append({"jsonpath": path, "validation": validation})
            
            if validation["success"]:
                return {
                    "success": True,
                    "jsonpath": path,
                    "metadata": {"attempts": attempts}
                }
            
            prompt += f"\n\nPrevious attempt {path} failed: {validation['issue']}. Try again."
            
        except Exception as e:
            attempts.append({"error": str(e)})

    return {"success": False, "error": "Max retries exceeded", "attempts": attempts}

def _validate_path(json_str: str, path: str, examples: List[str]) -> Dict[str, Any]:
    try:
        data = json.loads(json_str)
        expr = parse_path(path)
        matches = [str(m.value) for m in expr.find(data)]
        
        extracted_set = set(matches)
        
        found_count = 0
        for ex in examples:
            if ex in extracted_set:
                found_count += 1
            elif any(ex in m for m in matches): # partial
                found_count += 1
                
        if found_count == 0:
            return {"success": False, "issue": "No examples found"}
            
        return {"success": True, "count": len(matches)}
        
    except Exception as e:
        return {"success": False, "issue": str(e)}

def _parse_json(text: str) -> Dict:
    try:
        return json.loads(text)
    except:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {}
