
import json
import logging
import re
from typing import List, Dict, Any, Optional

from shared.llm_client import LLMClient
from .prompts import (
    FILTER_VALUES_USER_TEMPLATE,
    ATTRIBUTE_EXTRACTION_DIRECT_USER_TEMPLATE,
    SELECT_BEST_CANDIDATE_USER_TEMPLATE,
    FIND_MATCHING_TEXT_ATTRIBUTE_USER_TEMPLATE,
    FIND_MATCHING_TEXT_CONTENT_USER_TEMPLATE,
    FIND_STRUCTURED_EXAMPLES_USER_TEMPLATE,
    HTML_FIELD_REGEX_USER_TEMPLATE,
    HTML_FIELD_REGEX_SYSTEM_PROMPT
)
from .utils import extract_snippet

logger = logging.getLogger(__name__)

def filter_values_via_llm(values: List[str], target: str, llm: LLMClient) -> List[str]:
    """Use LLM to filter out noise from extracted attribute values."""
    if not values:
        return []
    
    # Deduplicate
    unique_values = list(dict.fromkeys(values))
    
    chunk = unique_values[:100]
    
    prompt = FILTER_VALUES_USER_TEMPLATE.format(
        target=target,
        chunk=chunk
    )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = json.loads(resp)
        valid = data.get("valid_values", [])
        
        if len(unique_values) > 100:
            pass
            
        return [str(v) for v in valid]
    except Exception as e:
        logger.warning(f"LLM filtering failed: {e}")
        return unique_values # Fallback: return original list

def extract_attribute_via_llm(html_content: str, text_examples: List[str], target: str, attribute: str, llm: LLMClient) -> List[str]:
    """Use LLM to extract attributes from HTML when regex approach fails."""
    # Find snippets around the text examples
    snippets = []
    for ex in text_examples[:3]:
        idx = html_content.lower().find(ex.lower())
        if idx != -1:
            snippet = extract_snippet(html_content, idx, len(ex), context=500)
            snippets.append(snippet)
    
    if not snippets:
        snippets = [html_content[:10000]]
    
    combined_snippets = "\n---\n".join(snippets[:3])[:15000]
    
    prompt = ATTRIBUTE_EXTRACTION_DIRECT_USER_TEMPLATE.format(
        attribute=attribute,
        target=target,
        text_examples=text_examples[:5],
        combined_snippets=combined_snippets
    )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = json.loads(resp)
        
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

def select_best_candidate_via_llm(candidates: List[Dict], intent: Dict, llm: LLMClient) -> Dict[str, Any]:
    """Step 4: Present candidate snippets to LLM and select the best one."""
    if not candidates:
        return {}
    
    options = []
    for i, c in enumerate(candidates):
        options.append(f"Option {i}: ...{c['snippet']}...")
    
    prompt = SELECT_BEST_CANDIDATE_USER_TEMPLATE.format(
        target=intent.get('target'),
        keywords=intent.get('keywords'),
        options="\n".join(options[:5])
    )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = json.loads(resp)
        idx = data.get("best_option_index")
        if idx is not None and 0 <= idx < len(candidates):
            return candidates[idx]
    except Exception:
        pass
    
    return candidates[0]

def find_matching_text_via_llm(inner_text: str, target: str, llm: LLMClient, is_attribute_target: bool = False) -> List[str]:
    """Step 2: Use LLM to find raw text matching the keyword in inner_text."""
    snippet = inner_text[:32768]
    
    if is_attribute_target:
        prompt = FIND_MATCHING_TEXT_ATTRIBUTE_USER_TEMPLATE.format(
            target=target,
            snippet=snippet
        )
    else:
        prompt = FIND_MATCHING_TEXT_CONTENT_USER_TEMPLATE.format(
            target=target,
            snippet=snippet
        )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = json.loads(resp)
        
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

def find_structured_examples_via_llm(text: str, target: str, keywords: List[str], llm: LLMClient) -> List[str]:
    """Find complete structured record examples for multi-field extraction."""
    snippet = text[:32768]
    fields_str = ", ".join(keywords[:5])
    
    prompt = FIND_STRUCTURED_EXAMPLES_USER_TEMPLATE.format(
        fields_str=fields_str,
        snippet=snippet
    )
    
    try:
        resp = llm.generate_text(prompt, extra_params={"response_format": {"type": "json_object"}})
        data = json.loads(resp)
        
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

def generate_field_regex(field_name: str, examples: List[str], html_content: str, llm: LLMClient) -> Optional[Dict[str, str]]:
    """Generate a regex pattern for a single field based on examples found in HTML."""
    if not examples:
        return None
    
    # Find where examples appear in HTML to get context - use more examples and larger context
    snippets = []
    for ex in examples[:5]:  # Use first 5 examples for better pattern detection
        if not ex:
            continue
        # Escape special regex chars for searching
        escaped_ex = re.escape(str(ex))
        # Try to find the example in HTML
        match = re.search(escaped_ex, html_content)
        if match:
            idx = match.start()
            # Larger context window (300 chars each side) to capture full HTML structure
            start = max(0, idx - 300)
            end = min(len(html_content), idx + len(str(ex)) + 300)
            snippet = html_content[start:end]
            # Avoid duplicate snippets
            if snippet not in snippets:
                snippets.append(snippet)
    
    if not snippets:
        logger.warning(f"No HTML snippets found for field '{field_name}' with examples: {examples[:3]}")
        return None
    
    # Show more examples to LLM
    examples_text = chr(10).join(f'- "{ex}"' for ex in examples[:10])
    snippet_text = "\n---\n".join(snippets[:5])
    
    prompt = HTML_FIELD_REGEX_USER_TEMPLATE.format(
        field_name=field_name,
        example_count=len(examples),
        examples_text=examples_text,
        snippet_text=snippet_text
    )

    try:
        messages = [
            {
                "role": "system", 
                "content": HTML_FIELD_REGEX_SYSTEM_PROMPT
            },
            {"role": "user", "content": prompt}
        ]
        # Use temperature=0 for maximum consistency and rule-following
        raw = llm.chat(messages, temperature=0.0, extra_params={"top_p": 0.1})
        
        # Parse response
        match = re.search(r'\{[^{}]*"regex"[^{}]*\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
            regex_pattern = result.get("regex", "")
            flags = result.get("flags", "s")
            
            # Handle intentionally empty regex (LLM couldn't find reliable pattern)
            if not regex_pattern:
                logger.info(f"LLM returned empty regex for '{field_name}' - no reliable structural pattern found")
                return None
            
            # Log the generated regex for debugging
            logger.info(f"Generated regex for '{field_name}': {regex_pattern[:150]}... (flags: {flags})")
            
            return {"regex": regex_pattern, "flags": flags}
        
        logger.warning(f"Failed to parse regex response for {field_name}: {raw[:200]}")
    except Exception as e:
        logger.warning(f"Failed to generate regex for {field_name}: {e}")
    
    return None
