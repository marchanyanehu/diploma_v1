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
import html
import re

__all__ = [
    "build_generation_messages",
    "build_refinement_messages",
    "validate_regex",
    "validate_attribute_regex",
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
    '{"regex": "##\\\\s*(?P<title>[^\\\\n]+)\\\\s*\\\\n\\\\s*\\\\[LINK:\\\\s*VIEW\\\\]\\\\s*\\\\((?P<url>[^\\\\)]+)\\\\)",'
    ' "flags": "s", "extraction_mode": "group",'
    ' "explanation": "Extract title and link using named groups from semantic content",'
    ' "confidence": 0.9}'
)


def _examples_block(examples: Sequence[str]) -> str:
    cleaned = [e.replace("\n", " ").strip() for e in examples if e.strip()]
    return "\n".join(f"- {c}" for c in cleaned[:10])  # cap examples for token economy


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _normalize_text_for_compare(text: str, *, lowercase: bool = False) -> str:
    """Normalize text for robust comparison between HTML-captured strings and LLM examples.

    - strips HTML tags
    - decodes HTML entities (&amp; -> &)
    - normalizes whitespace
    """
    if not text:
        return ""
    # Strip HTML tags if the regex accidentally captured markup.
    stripped = _TAG_RE.sub(" ", text)
    # Decode entities (headless HTML commonly contains &amp; etc.)
    stripped = html.unescape(stripped)
    # Normalize whitespace incl. non-breaking space
    stripped = stripped.replace("\xa0", " ")
    stripped = _WS_RE.sub(" ", stripped).strip()
    if lowercase:
        stripped = stripped.lower()
    return stripped


def _find_example_position_in_source(source: str, example: str) -> int | None:
    """Find an example text in raw HTML source.

    Examples often come from LLM semantic text extraction (decoded entities), while the raw HTML
    still contains entity-escaped variants. We try a few variants to locate the anchor.
    """
    if not example:
        return None

    candidates: list[str] = [example]
    # HTML-escaped variants (important for & -> &amp; etc.).
    escaped_no_quote = html.escape(example, quote=False)
    if escaped_no_quote != example:
        candidates.append(escaped_no_quote)
    escaped_quote = html.escape(example, quote=True)
    if escaped_quote not in candidates:
        candidates.append(escaped_quote)

    for cand in candidates:
        idx = source.find(cand)
        if idx != -1:
            return idx

    # Case-insensitive fallback
    lower_source = source.lower()
    for cand in candidates:
        idx = lower_source.find(cand.lower())
        if idx != -1:
            return idx

    return None


def _select_snippet_from_source(source: str, examples: Sequence[str], *, max_len: int = 32000) -> str:
    """Pick a snippet likely containing example anchors from a large HTML source.

    This prevents prompting the LLM with unrelated <head> content when examples are far
    down the document (common with headless full-page HTML).
    """
    # Try to anchor snippet around the first example we can locate in the source.
    for ex in examples[:10]:
        pos = _find_example_position_in_source(source, ex)
        if pos is None:
            continue

        half = max_len // 2
        start = max(0, pos - half)
        end = min(len(source), start + max_len)
        return source[start:end]

    # Fallback: beginning of the document.
    return source[:max_len]


def _snippet_contains_any_example(snippet: str, examples: Sequence[str]) -> bool:
    """Heuristic: does the provided snippet likely include the relevant region?

    Callers may pass a snippet derived from semantic text (innerText). For raw HTML sources this
    snippet can miss the actual anchors due to entity encoding differences. If we can't find any
    example (or its escaped variant) in the snippet, we should re-select from the full source.
    """
    if not snippet:
        return False
    for ex in examples[:10]:
        if not ex:
            continue
        if ex in snippet:
            return True
        escaped = html.escape(ex, quote=False)
        if escaped != ex and escaped in snippet:
            return True
    return False


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
            if not ex:
                continue
            # Prefer marking the exact example; fallback to marking its HTML-escaped variant.
            if ex in marked_snippet:
                marked_snippet = marked_snippet.replace(ex, f"[[EXAMPLE→]]{ex}[[←EXAMPLE]]", 1)
                continue
            escaped = html.escape(ex, quote=False)
            if escaped != ex and escaped in marked_snippet:
                marked_snippet = marked_snippet.replace(escaped, f"[[EXAMPLE→]]{escaped}[[←EXAMPLE]]", 1)
        
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
    max_matches: int = 200,
    expected_fields: Sequence[str] | None = None
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

    # Simple catastrophic backtracking heuristic (cheap, not exhaustive)
    if re.search(r"\(\s*\.\*\s*\)\s*\*|\(\s*\.\+\s*\)\s*\+|\(\s*\.\*\s*\)\s*\+|\(\s*\.\+\s*\)\s*\*", pattern):
        result["issues"].append("Potential catastrophic quantifier nesting detected")
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
        
    # Check for named groups if multiple fields are expected
    if expected_fields and len(expected_fields) > 1:
        group_names = set(rx.groupindex.keys())
        missing_groups = [f for f in expected_fields if f not in group_names]
        if missing_groups:
            result["issues"].append(f"Missing named capturing groups: {', '.join(missing_groups)}")
        
    # 3. Run Matches (with safety limits)
    matches = []
    has_named_groups = bool(rx.groupindex)
    
    try:
        for i, m in enumerate(rx.finditer(source)):
            if i >= max_matches:
                result["issues"].append(f"Too many matches (capped at {max_matches})")
                break
                
            if has_named_groups:
                # For named groups, we create a composite string for validation
                gd = m.groupdict()
                matches.append(" | ".join(f"{k}: {v}" for k, v in gd.items() if v))
            elif m.lastindex and m.lastindex >= 1:
                matches.append(m.group(1))
            else:
                matches.append(m.group(0))
    except Exception as e:
        result["error"] = f"Runtime match error: {str(e)}"
        return result
        
    # Filter out None values
    matches = [m for m in matches if m is not None]
    result["matches"] = matches
    # Preserve order while deduping
    result["distinct_matches"] = list(dict.fromkeys(matches))
    
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

    missing = []
    lowercase = 'i' in flags

    # Optimization: sets for fast lookups
    raw_match_set = {m.lower() for m in matches} if lowercase else set(matches)
    normalized_matches = [_normalize_text_for_compare(m, lowercase=lowercase) for m in matches]
    normalized_match_set = set(normalized_matches)
        
    for ex in examples:
        if not ex:
            continue

        # For JSON-like examples (multi-field), we check if the components match
        if ex.startswith('{') and ex.endswith('}'):
            try:
                ex_data = json.loads(ex)
                if isinstance(ex_data, dict):
                    # Check if ANY match contains these field values
                    found_composite = False
                    for norm_m in normalized_matches:
                        # CRITICAL: if a field is expected but missing in regex match, this should fail.
                        # We only allow skipping values that are TRULY empty in the LLM example.
                        valid_vals = [v for v in ex_data.values() if v]
                        if not valid_vals: # Example was empty? Skip it.
                            found_composite = True
                            break
                        
                        if all(_normalize_text_for_compare(str(v), lowercase=lowercase) in norm_m for v in valid_vals):
                            found_composite = True
                            break
                    if found_composite:
                        continue
            except Exception:
                pass

        check_ex = ex.lower() if lowercase else ex
        normalized_ex = _normalize_text_for_compare(ex, lowercase=lowercase)
        if not normalized_ex:
            continue

        # Check 1: Exact raw match
        if check_ex in raw_match_set:
            continue
            
        # Check 2: Exact normalized match (handles entities, whitespace, accidental markup)
        if normalized_ex in normalized_match_set:
            continue

        # Check 3: Normalized containment (tolerant for cases where capture includes extra nearby text)
        found = False
        for norm_match in normalized_matches:
            if not norm_match:
                continue
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


def validate_attribute_regex(
    pattern: str,
    source: str,
    anchors: Sequence[str],
    *,
    flags: str = "",
    max_matches: int = 200,
    anchor_window: int = 8000,
    min_anchor_coverage: float = 0.6,
) -> Dict[str, Any]:
    """Validate attribute-extraction regexes (href/src/etc.) against raw HTML.

    In this mode, provided `anchors` are *not* the captured values. They are nearby texts that should
    help localize the target attribute. We validate by requiring the regex to find at least one match
    in a window around a significant fraction of anchors.

    Returns a dict similar to `validate_regex` with additional anchor diagnostics.
    """
    result: Dict[str, Any] = {
        "success": False,
        "matches": [],
        "issues": [],
        "error": None,
        "missing_anchors": [],
        "anchor_found": 0,
        "anchor_covered": 0,
        "anchor_coverage": 0.0,
        "pattern": pattern,
    }

    if not pattern or len(pattern) > 500:
        result["issues"].append("Pattern empty or too long (>500 chars)")
        return result

    # Compile Regex
    re_flags = 0
    if 'i' in flags: re_flags |= re.IGNORECASE
    if 'm' in flags: re_flags |= re.MULTILINE
    if 's' in flags: re_flags |= re.DOTALL
    try:
        rx = re.compile(pattern, re_flags)
    except Exception as e:
        result["error"] = str(e)
        return result

    # Collect matches from the full source (capped)
    matches: list[str] = []
    try:
        for i, m in enumerate(rx.finditer(source)):
            if i >= max_matches:
                result["issues"].append(f"Too many matches (capped at {max_matches})")
                break
            val = m.group(1) if (m.lastindex and m.lastindex >= 1) else m.group(0)
            if val is None:
                continue
            matches.append(val.strip())
    except Exception as e:
        result["error"] = f"Runtime match error: {str(e)}"
        return result

    matches = [m for m in matches if m]
    result["matches"] = matches
    result["distinct_matches"] = list(dict.fromkeys(matches))

    if not matches:
        result["issues"].append("No matches found in source")
        return result

    # Anchor coverage check
    found = 0
    covered = 0
    missing_anchors: list[str] = []

    half = max(500, anchor_window // 2)
    for a in anchors:
        if not a:
            continue
        pos = _find_example_position_in_source(source, a)
        if pos is None:
            missing_anchors.append(a)
            continue

        found += 1
        start = max(0, pos - half)
        end = min(len(source), pos + half)
        window_text = source[start:end]

        if rx.search(window_text):
            covered += 1

    result["missing_anchors"] = missing_anchors
    result["anchor_found"] = found
    result["anchor_covered"] = covered
    result["anchor_coverage"] = (covered / found) if found else 0.0

    if found == 0:
        result["issues"].append("None of the provided anchors were found in source")
    elif result["anchor_coverage"] < min_anchor_coverage:
        result["issues"].append(
            f"Low anchor coverage: {covered}/{found} anchors had a nearby match (threshold {min_anchor_coverage})"
        )

    # Attribute extraction patterns should not be wildly broad.
    unique = len(set(matches))
    broad_threshold = max(found * 50, 500)  # generous but still blocks 'everything in <head>' patterns
    if unique > broad_threshold:
        result["issues"].append(f"Pattern too broad for attribute mode: {unique} unique matches (threshold {broad_threshold})")

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
    is_attribute_extraction: bool = False,
    expected_fields: Sequence[str] | None = None
) -> Dict[str, Any]:
    """Run iterative loop until success or exhaustion."""
    if not examples:
        return {"success": False, "error": "no examples"}
    # Ensure snippet_used is robust for JSON/large content:
    # - callers may pass a snippet that doesn't contain anchors due to HTML entity encoding
    # - for large raw HTML, we must pick a window around the anchors (examples)
    if snippet is not None and len(snippet) > 100 and _snippet_contains_any_example(snippet, examples):
        snippet_used = snippet
    else:
        snippet_used = _select_snippet_from_source(source, examples)
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
    
    if is_attribute_extraction:
        val = validate_attribute_regex(pattern, source, examples, flags=flags)
    else:
        val = validate_regex(pattern, source, examples, flags=flags, expected_fields=expected_fields)
    
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
        if is_attribute_extraction:
            val_ref = validate_attribute_regex(pattern_ref, source, examples, flags=flags_ref)
        else:
            val_ref = validate_regex(pattern_ref, source, examples, flags=flags_ref, expected_fields=expected_fields)

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
