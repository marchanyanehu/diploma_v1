
import json
import re
from typing import Any, Dict, List, Optional, Union
import logging

try:
    from parsel import Selector
except ImportError:
    Selector = None

try:
    from jsonpath_ng import parse as parse_app
except ImportError:
    parse_app = None

# Import regex generation as fallback strategy
from . import regex_generation
from . import css_selector_generation
from . import json_path_generation

logger = logging.getLogger(__name__)

def generate_parser(
    content: str,
    examples: List[Union[str, Dict]],
    target_desc: str,
    llm: Any,
    source_type_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate the best parser for the given content and examples.
    
    Args:
        content: The raw content (HTML, JSON, or text)
        examples: List of examples to extract
        target_desc: Description of what to extract (e.g. "job titles")
        llm: LLM client wrapper
        source_type_hint: Optional hint ('HTML', 'JSON', 'TEXT')
    
    Returns:
        Dict with keys: success, pattern, source_type, flags, metadata
    """
    
    # 1. Detect content type if not provided
    content_type = source_type_hint or _detect_content_type(content)
    logger.info(f"Generating parser for content_type={content_type}")

    # 2. Add 'CSS' Strategy for HTML
    if content_type == "HTML":
        # Check if parsel is available
        if Selector:
            logger.info("Attempting CSS Selector generation...")
            result = css_selector_generation.generate_css_selector(
                html_content=content,
                examples=examples,
                target_desc=target_desc,
                llm=llm
            )
            if result.get("success"):
                return {
                    "success": True,
                    "pattern": result["selector"],
                    "source_type": "CSS",
                    "flags": result.get("attribute", ""), # Store attribute to extract (text, href, etc.)
                    "metadata": result.get("metadata", {})
                }
            logger.warning("CSS Selector generation failed, falling back to Regex.")
        else:
            logger.warning("parsel not installed, skipping CSS generation.")

    # 3. Add 'JSONPATH' Strategy for JSON
    elif content_type == "JSON":
        if parse_app:
            logger.info("Attempting JSONPath generation...")
            result = json_path_generation.generate_json_path(
                json_content=content,
                examples=examples,
                target_desc=target_desc,
                llm=llm
            )
            if result.get("success"):
                return {
                    "success": True,
                    "pattern": result["jsonpath"],
                    "source_type": "JSONPATH",
                    "flags": "",
                    "metadata": result.get("metadata", {})
                }
            logger.warning("JSONPath generation failed, falling back to Regex.")
        else:
            logger.warning("jsonpath-ng not installed, skipping JSONPath generation.")

    # 4. Fallback: Regex
    # Regex works for everything (brute force)
    logger.info("Falling back to Regex generation...")
    result = regex_generation.iterative_regex_generation(
        source=content,
        examples=examples,
        target_desc=target_desc,
        llm=llm,
        max_iterations=2
    )
    
    if result.get("success"):
        return {
            "success": True,
            "pattern": result["final_pattern"],
            "source_type": "REGEX",
            "flags": result.get("final_flags", "s"),
            "metadata": {"attempts": len(result.get("attempts", []))}
        }
        
    return {"success": False, "error": result.get("error", "Unknown failure")}


def execute_parser(
    source_type: str,
    pattern: str,
    content: str,
    flags: str = "",
    min_matches: int = 1
) -> List[Dict[str, Any]]:
    """
    Execute a stored parser against content.
    """
    matches = []
    
    # Strategy: CSS
    if source_type == "CSS":
        if not Selector:
            return []
        try:
            sel = Selector(text=content)
            # Pattern is the CSS selector
            # Flags might contain the attribute to extract (e.g. '::text', '::attr(href)')
            # But standard CSS selectors don't support pseudo-elements for extraction in all libraries.
            # We'll assume the pattern selects the ELEMENT, and flags tells us what to take.
            # Or we follow the parsel convention: "div.foo::text" vs "div.foo::attr(href)"
            
            # Implementation detail: The generator should return a selector that INCLUDES the extraction logic 
            # if the library supports it (parsel supports ::text and ::attr(x)).
            # EXCEPT standard CSS doesn't.
            # Let's assume pattern is full parsel-compatible selector (e.g. 'a.job::attr(href)')
            
            extracted = sel.css(pattern).getall()
            matches = [{"text": str(x).strip(), "source": "CSS"} for x in extracted if x and str(x).strip()]
            
        except Exception as e:
            logger.error(f"CSS execution failed: {e}")
            return []

    # Strategy: JSONPATH
    elif source_type == "JSONPATH":
        if not parse_app:
            return []
        try:
            json_data = json.loads(content)
            jsonpath_expr = parse_app(pattern)
            results = jsonpath_expr.find(json_data)
            matches = [{"text": str(r.value), "source": "JSONPATH"} for r in results]
        except Exception as e:
            logger.error(f"JSONPath execution failed: {e}")
            return []
            
    # Strategy: REGEX (handles SEMANTIC, HTML, JSON stored as regex patterns)
    elif source_type in ["REGEX", "SEMANTIC", "HTML", "JSON"]:
        from .utils import apply_regex_matches
        raw_matches = apply_regex_matches(pattern, flags, content)
        matches = raw_matches # structured dicts

    # Filter empty
    return [m for m in matches if m]

def _detect_content_type(content: str) -> str:
    """Simple heuristic to detect content type."""
    content = content.strip()
    if content.startswith("<") and ">" in content:
        # Check for common HTML tags
        if "<html" in content.lower() or "<div" in content.lower() or "<body" in content.lower():
            return "HTML"
    
    if (content.startswith("{") and content.endswith("}")) or \
       (content.startswith("[") and content.endswith("]")):
        try:
            json.loads(content)
            return "JSON"
        except:
            pass
            
    return "TEXT"
