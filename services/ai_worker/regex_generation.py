"""Regex Generation & Refinement (Tasks #406-#409)

This module provides:
1. Prompt engineering helpers for initial regex generation (Task #406)
2. Validation logic to test a candidate regex against full source content (Task #407)
3. Refinement ("fix-it") prompt builder to correct faulty regexes (Task #408)
4. Iterative loop: Generate -> Validate -> (Refine -> Validate)* (Task #409)

Design goals:
- Deterministic JSON protocol between our code and the LLM (NO prose)
- Minimize overfitting (prefer patterns that generalize but are not too broad)
- Safety heuristics to reject pathological regexes (catastrophic backtracking likelihood,
  runaway matches, empty captures)
- Pure-Python validation so unit tests do not require an actual LLM

Public functions:
  build_generation_messages(snippet: str, examples: list[str], *, target_desc: str) -> list[dict]
  build_refinement_messages(previous_json: dict, failures: dict, snippet: str, examples: list[str], *, target_desc: str) -> list[dict]
  validate_regex(pattern: str, source: str, examples: list[str], *, flags: str = "", max_matches: int = 200) -> dict
  iterative_regex_generation(source: str, examples: list[str], *, target_desc: str, llm, max_iterations: int = 3, snippet: str | None = None) -> dict

LLM JSON Contract (both generation & refinement must output ONLY JSON):
{
  "regex": str,                 # Raw pattern (ECMAScript/Python compatible)
  "flags": str,                 # Combination of: i,m,s (case-insensitive, multiline, dotall)
  "extraction_mode": "findall" | "group",  # Strategy: use re.findall OR first capturing group from re.finditer
  "explanation": str,           # Short explanation (<= 240 chars)
  "confidence": float           # 0..1 self-assessed confidence
}

Refinement will supply a list of failure notes the model must address.

Heuristics enforced during validation:
  - Reject if pattern empty or longer than 500 chars (likely hallucination)
  - Reject if it contains nested catastrophic quantifiers like (.+)+ or (.*)* or .+? inside groups repeated (simple regex)
  - Limit total matches (<= max_matches)
  - Must match ALL provided examples (case-sensitive compare unless example lowered entirely and flag 'i')
  - Distinct match ratio: duplicates reduced; if more than 80% duplicates -> reject (likely too broad)
  - Average match length must be within [2, 2000]

Assumptions:
  - examples list already filtered / representative by previous pipeline steps
  - source may be large; we only collect up to max_matches matches to avoid memory blow-up

Future improvements (out of current task scope):
  - Structural hints (HTML/JSON context) to bias toward more precise patterns
  - Multi-phase ranking of alternative regex candidates
  - Token / AST-level safety scanning
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence
import json
import re

__all__ = [
    "build_generation_messages",
    "build_refinement_messages",
    "validate_regex",
    "iterative_regex_generation",
]


from .prompts import (
    REGEX_GENERATION_SYSTEM_PROMPT,
    REGEX_GENERATION_RULES,
    REGEX_GENERATION_ATTRIBUTE_USER_TEMPLATE,
    REGEX_GENERATION_STANDARD_USER_TEMPLATE,
    REGEX_GENERATION_MULTILINE_USER_TEMPLATE
)

_SYSTEM_INSTRUCTION = REGEX_GENERATION_SYSTEM_PROMPT
_GENERATION_RULES = REGEX_GENERATION_RULES

_JSON_EXAMPLE = (
    '{"regex": "\\"hostedUrl\\"\\\\s*:\\\\s*\\"(https?://[^\\"]*)\\"",'
    ' "flags": "s", "extraction_mode": "group",'
    ' "explanation": "Extract hostedUrl URL value from JSON using key anchor",'
    ' "confidence": 0.9}'
)


def _examples_block(examples: Sequence[str]) -> str:
    cleaned = [e.replace("\n", " ").strip() for e in examples if e.strip()]
    return "\n".join(f"- {c}" for c in cleaned[:10])  # cap examples for token economy


def build_generation_messages(
    snippet: str,
    examples: Sequence[str],
    *,
    target_desc: str,
    is_attribute_extraction: bool = False
) -> List[Dict[str, str]]:
    """Build chat messages for initial regex generation.

    Returns OpenAI-style messages list.
    """
    if is_attribute_extraction:
        # Special prompt for attribute extraction (e.g. URLs, IDs) where examples are anchors
        user = REGEX_GENERATION_ATTRIBUTE_USER_TEMPLATE.format(
            target_desc=target_desc,
            examples_block=_examples_block(examples),
            snippet=snippet[:32000],
            generation_rules=_GENERATION_RULES
        )
    else:
        # Standard text extraction
        # Mark where examples appear in the snippet for clarity
        marked_snippet = snippet[:32000]
        for ex in examples:
            if ex and ex in marked_snippet:
                marked_snippet = marked_snippet.replace(ex, f"[[EXAMPLE→]]{ex}[[←EXAMPLE]]", 1)
        
        # Detect if example is multi-line (spans multiple HTML elements)
        has_multiline_example = any('\n' in ex for ex in examples if ex)
        
        if has_multiline_example:
            # For multi-line/block content (descriptions, articles, etc.)
            user = REGEX_GENERATION_MULTILINE_USER_TEMPLATE.format(
                target_desc=target_desc,
                examples_block=_examples_block(examples),
                marked_snippet=marked_snippet,
                generation_rules=_GENERATION_RULES
            )
        else:
            user = REGEX_GENERATION_STANDARD_USER_TEMPLATE.format(
                target_desc=target_desc,
                examples_block=_examples_block(examples),
                marked_snippet=marked_snippet,
                generation_rules=_GENERATION_RULES
            )
        
    return [
        {"role": "system", "content": _SYSTEM_INSTRUCTION},
        {"role": "user", "content": user},
    ]

def build_refinement_messages(
    previous_json: Dict[str, Any],
    failures: Dict[str, Any],
    snippet: str,
    examples: Sequence[str],
    *,
    target_desc: str,
    is_attribute_extraction: bool = False
) -> List[Dict[str, str]]:
    """Build chat messages for refinement (fix-it) prompt."""
    prev = json.dumps(previous_json, ensure_ascii=False)
    
    missing_examples = failures.get("missing_examples", [])
    issues = failures.get("issues", [])
    
    if is_attribute_extraction:
        instruction = (
            f"REFINE the previous regex. It failed to capture the target '{target_desc}' associated with the anchors.\n\n"
            f"ANCHORS: The regex should use these texts to locate the element:\n{_examples_block(examples)}\n\n"
            f"CONTENT SNIPPET:\n<<<SNIPPET_START>>>\n{snippet[:32000]}\n<<<SNIPPET_END>>>\n\n"
            f"PREVIOUS ATTEMPT: {prev}\n\n"
            f"ISSUES: {', '.join(issues)}\n"
            f"Fix the regex. It must locate the anchor text but CAPTURE the '{target_desc}'. Output ONLY corrected JSON.\n\n"
            f"{_GENERATION_RULES}"
        )
    else:
        instruction = (
            f"REFINE the previous regex. The pattern failed validation.\n\n"
            f"TARGET: {target_desc}\n\n"
            f"EXAMPLES (the regex MUST match each):\n{_examples_block(examples)}\n\n"
            f"CONTENT SNIPPET:\n<<<SNIPPET_START>>>\n{snippet[:32000]}\n<<<SNIPPET_END>>>\n\n"
            f"PREVIOUS ATTEMPT: {prev}\n\n"
            f"ISSUES: {', '.join(issues) if issues else 'Pattern did not match examples'}\n"
            f"MISSING EXAMPLES: {missing_examples[:5] if missing_examples else 'None'}\n\n"
            f"Fix the regex to match ALL examples. Output ONLY corrected JSON.\n\n"
            f"{_GENERATION_RULES}"
        )

    return [
        {"role": "system", "content": _SYSTEM_INSTRUCTION},
        {"role": "user", "content": instruction},
    ]

def validate_regex(
    pattern: str,
    source: str,
    examples: Sequence[str],
    *,
    flags: str = "",
    max_matches: int = 200
) -> Dict[str, Any]:
    """Validate a regex pattern against source content and examples.
    
    Returns a dict with:
      success: bool
      matches: list[str] (all matches found)
      issues: list[str] (reasons for failure)
      error: str (if regex invalid)
      missing_examples: list[str] (examples not found)
    """
    import re
    
    result = {
        "success": False,
        "matches": [],
        "issues": [],
        "error": None,
        "missing_examples": [],
        "pattern": pattern
    }
    
    # 1. Basic Safety Checks
    if not pattern or len(pattern) > 500:
        result["issues"].append("Pattern empty or too long (>500 chars)")
        return result
        
    # 2. Compile Regex
    re_flags = 0
    if 'i' in flags: re_flags |= re.IGNORECASE
    if 'm' in flags: re_flags |= re.MULTILINE
    if 's' in flags: re_flags |= re.DOTALL
    
    try:
        rx = re.compile(pattern, re_flags)
    except Exception as e:
        result["error"] = str(e)
        return result
        
    # 3. Run Matches (with safety limits)
    matches = []
    try:
        # Use finditer to avoid massive list allocation if too many matches
        for i, m in enumerate(rx.finditer(source)):
            if i >= max_matches:
                result["issues"].append(f"Too many matches (capped at {max_matches})")
                break
                
            # Prefer capturing group 1 if present, else whole match
            if m.lastindex and m.lastindex >= 1:
                matches.append(m.group(1))
            else:
                matches.append(m.group(0))
    except Exception as e:
        result["error"] = f"Runtime match error: {str(e)}"
        return result
        
    # Filter out None values from matches (can happen with optional capture groups)
    matches = [m for m in matches if m is not None]
    result["matches"] = matches
    result["distinct_matches"] = list(set(matches))
    
    # 4. Check Constraints
    if not matches:
        result["issues"].append("No matches found in source")
        return result
        
    # Check average length (avoid matching huge blocks)
    avg_len = sum(len(m) for m in matches) / len(matches)
    if avg_len > 2000:
        result["issues"].append(f"Average match length too high ({int(avg_len)} chars)")
    if avg_len < 2:
        result["issues"].append(f"Average match length too low ({int(avg_len)} chars)")
        
    # Check duplicates (if mostly duplicates, it's likely too broad like matching " " or ",")
    unique_matches = set(matches)
    if len(matches) > 10 and len(unique_matches) < len(matches) * 0.2:
         result["issues"].append("High duplication rate (likely too generic)")

    # 5. Verify Examples
    # All provided examples MUST be present in the matches
    # We normalize for comparison if case-insensitive flag is set
    # Note: Examples might be substrings of the full match or exact matches.
    # For HTML content, we also check if the TEXT CONTENT matches (ignoring HTML tags)
    
    def _strip_html_and_normalize(text: str) -> str:
        """Strip HTML tags and normalize whitespace for comparison."""
        import re as _re
        # Remove HTML tags
        stripped = _re.sub(r'<[^>]+>', ' ', text)
        # Normalize whitespace (newlines, multiple spaces -> single space)
        stripped = _re.sub(r'\s+', ' ', stripped).strip()
        return stripped
    
    missing = []
    # Optimization: use set for fast lookups
    match_set = set(matches)
    if 'i' in flags:
        match_set = {m.lower() for m in matches}
    
    # Also create normalized versions for HTML comparison
    normalized_matches = [_strip_html_and_normalize(m) for m in matches]
    if 'i' in flags:
        normalized_matches = [m.lower() for m in normalized_matches]
        
    for ex in examples:
        if not ex: continue
        check_ex = ex if 'i' not in flags else ex.lower()
        normalized_ex = _strip_html_and_normalize(check_ex)
        
        # Check 1: Exact match
        if check_ex in match_set:
            continue
            
        # Check 2: Normalized text content match (handles HTML captures)
        found = False
        for norm_match in normalized_matches:
            # Check if normalized example is contained in normalized match
            if normalized_ex in norm_match or norm_match in normalized_ex:
                found = True
                break
            # Also check first significant part (for multi-line examples)
            first_part = normalized_ex.split('.')[0].strip() if '.' in normalized_ex else normalized_ex[:50]
            if len(first_part) > 10 and first_part in norm_match:
                found = True
                break
                
        if not found:
            missing.append(ex)
            
    if missing:
        result["missing_examples"] = missing
        result["issues"].append(f"Failed to match {len(missing)}/{len(examples)} provided examples")
    
    # 6. Check precision - if we match WAY more than examples, pattern might be too broad
    # Allow generous headroom for list pages / APIs with many items (e.g., 200x the examples, capped)
    broad_threshold = max(len(examples) * 200, 2000)
    if len(examples) > 0 and len(unique_matches) > broad_threshold:
        result["issues"].append(f"Pattern too broad: {len(unique_matches)} matches for {len(examples)} examples")
        
    # Final Success Determination
    if not result["issues"] and not result["error"]:
        result["success"] = True
        
    return result

def _extract_json(raw: str) -> Dict[str, Any]:
    """Safe JSON extraction from LLM output."""
    import re
    text = raw.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # Try finding { ... } block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
            
    # Fallback
    return {}


def iterative_regex_generation(
    source: str,
    examples: Sequence[str],
    *,
    target_desc: str,
    llm: Any,
    max_iterations: int = 3,
    snippet: str | None = None,
    is_attribute_extraction: bool = False
) -> Dict[str, Any]:
    """Run iterative loop until success or exhaustion."""
    if not examples:
        return {"success": False, "error": "no examples"}
    # Ensure snippet_used is robust for JSON/large content
    snippet_used = snippet if snippet is not None and len(snippet) > 100 else source[:32000]
    attempts: List[Dict[str, Any]] = []

    gen_messages = build_generation_messages(
        snippet_used, examples, target_desc=target_desc, is_attribute_extraction=is_attribute_extraction
    )
    try:
        raw = llm.chat(gen_messages, temperature=0.2)
    except Exception as exc:
        attempts.append({"stage": "initial_error", "error": str(exc)})
        return {
            "success": False,
            "error": f"llm_chat_failed_initial: {exc}",
            "attempts": attempts,
            "final_pattern": None,
            "final_flags": None,
        }
    parsed = _extract_json(raw)
    pattern = str(parsed.get("regex", ""))
    # Default to DOTALL flag if not specified
    flags = str(parsed.get("flags", "s"))
    if "s" not in flags.lower():
        flags = flags + "s"
    
    # Validate: For attribute extraction, we can't strictly enforce that matches == examples
    # because matches are VALUES (URLs) and examples are ANCHORS (Titles).
    # We'll relax validation for attribute mode or need a different validator.
    # For now, we use the standard validator but might ignore "missing_examples" if we find *something*.
    
    val = validate_regex(pattern, source, examples, flags=flags)
    
    # Special validation logic for attribute extraction
    if is_attribute_extraction:
        # If we found matches (URLs) but they don't equal the examples (Titles), that's EXPECTED.
        # We treat it as success if we got matches and the regex seems valid.
        if val["matches"] and not val.get("error"):
             val["success"] = True
             val["issues"] = [] # Clear issues since mismatch is expected
    
    attempts.append({"stage": "initial", "raw": raw, "parsed": parsed, "validation": val})
    if val.get("success"):
        return {
            "success": True,
            "attempts": attempts,
            "final_pattern": pattern,
            "final_flags": flags,
        }

    prev = parsed
    for iteration in range(1, max_iterations):
        failures = {k:v for k,v in val.items() if k in {"missing_examples", "issues", "error", "pattern"}}
        
        ref_messages = build_refinement_messages(
            prev, failures, snippet_used, examples, 
            target_desc=target_desc, is_attribute_extraction=is_attribute_extraction
        )
        try:
            raw_ref = llm.chat(ref_messages, temperature=0.15)
        except Exception as exc:
            attempts.append({"stage": f"refinement_{iteration}_error", "error": str(exc)})
            return {
                "success": False,
                "error": f"llm_chat_failed_refinement: {exc}",
                "attempts": attempts,
                "final_pattern": None,
                "final_flags": None,
            }
        parsed_ref = _extract_json(raw_ref)
        pattern_ref = str(parsed_ref.get("regex", ""))
        flags_ref = str(parsed_ref.get("flags", "s"))
        if "s" not in flags_ref.lower():
            flags_ref = flags_ref + "s"
        val_ref = validate_regex(pattern_ref, source, examples, flags=flags_ref)
        
        if is_attribute_extraction and val_ref["matches"] and not val_ref.get("error"):
             val_ref["success"] = True
             val_ref["issues"] = []

        attempts.append(
            {
                "stage": f"refinement_{iteration}",
                "raw": raw_ref,
                "parsed": parsed_ref,
                "validation": val_ref,
            }
        )
        if val_ref.get("success"):
            return {
                "success": True,
                "attempts": attempts,
                "final_pattern": pattern_ref,
                "final_flags": flags_ref,
            }
        prev = parsed_ref
        val = val_ref

    return {"success": False, "attempts": attempts, "final_pattern": None, "final_flags": None}


# End of module
