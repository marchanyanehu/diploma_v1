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


# ---------------------------- Prompt Engineering --------------------------- #

_SYSTEM_INSTRUCTION = """You are a specialized AI assistant that generates **generalized, production-grade regular expressions** from provided JSON or HTML snippets.

## Global Assumptions
* **DOTALL is enabled** (`.` matches newlines). Do **not** add inline `(?s)`.
* **Never wrap** the regex in language/framework scopes or delimiters (no `/.../`, no flags outside the pattern).
* **Always escape curly braces** as `\\{` and `\\}` inside the pattern when matching literal braces.

## Generalization Rules (Must Follow)
Your regexes **must be reusable across pages/jobs with similar structure**. Do **not** bake in page-specific details.

**Avoid page-specific anchors**
* Do not use full URLs, numeric IDs that look auto-generated, GUIDs, timestamps, build hashes, or long opaque tokens.
* Do not bind to exact tag names (`div`, `h1`, `a`) if an attribute-level anchor exists. Prefer stable attributes.
* Do not rely on complete class lists; **bind to the stable, structural subset** of class names and allow variance around it.

**Prefer structural, tolerant anchors**
* Use stable `class`/`id` fragments; when binding by class, **omit styling/size/animation tokens** and allow other attributes via `[^>]*?`.
* Allow optional whitespace with lazy spacing (`\\s*?` or `\\s*`) near boundaries.
* When nested markup may appear, allow it with non-capturing skips like `(?:<[^>]+>)*`.
* Use **lazy quantifiers** and **tempered patterns** to avoid runaway greed.

**Capture only what you need**
* Use a **single capturing group** for the target value. Use `(?: ... )` for all non-target grouping.
* Trim leading/trailing whitespace in the capture by placing `\\s*` **outside** the group when appropriate.

**JSON-specific guidance**
* Keys: match with tolerance around separators: `"key"\\s*:\\s*"([^"]+)"`.
* For URL values: `"hostedUrl"\\s*:\\s*"(https?://[^"]+)"` or `"applyUrl"\\s*:\\s*"(https?://[^"]+)"`.
* String values: capture with `([^"]+)` for simple strings, `(https?://[^"]+)` for URLs.
* Arrays: `"items"\\s*:\\s*\\[` then iterate with `"url"\\s*:\\s*"([^"]+)"`.

**HTML-specific guidance**
* Anchor on **stable attribute fragments** (`class`, `id`) not tag names; allow attribute variability via `[^>]*?`.
* For href extraction: `href="(https?://[^"]+)"` with appropriate context anchors.
* Text extraction: anchor → allow attributes → optional whitespace → **capture inner text non-greedily** → stop at next tag.

## Safety & Performance
* Keep patterns as **specific as needed but no more**: prefer character classes/tempered tokens to `.*?` when a safe boundary exists.
* Avoid catastrophic backtracking: prefer `[^"]*` over `.*?` for JSON string capture.

You output ONLY strict JSON following the schema. Never include commentary, code fences, or additional text."""

_GENERATION_RULES = """## Output Format (Strict)
Output ONLY a JSON object with these keys:
- "regex": the raw pattern (no delimiters, properly escaped for JSON)
- "flags": combination of i,m,s (usually empty or "s")
- "extraction_mode": "group" (single capturing group) or "findall"
- "explanation": brief reason (<= 240 chars)
- "confidence": 0..1 self-assessed confidence

## Rules
1. Output ONLY JSON (no backticks, no prose).
2. Use non-greedy quantifiers. Avoid catastrophic backtracking.
3. Prefer explicit character classes over '.*' when possible.
4. Single capturing group for the target value only.
5. Generalize variable segments (use \\d+, [A-Za-z]+, etc. not literals).
6. Keep pattern length < 500 chars.
7. Escape literal special chars: . + ? ( ) [ ] { } | ^ $ /
8. Do NOT include page-specific IDs, GUIDs, timestamps, or full URLs in pattern."""

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
        user = (
            f"TARGET: {target_desc}\n"
            f"CONTEXT/ANCHORS: The following text strings appear near the target data (e.g. link text for a URL):\n{_examples_block(examples)}\n\n"
            f"CONTENT SNIPPET (generate a generalized regex that works on similar content):\n"
            f"<<<SNIPPET_START>>>\n{snippet[:32000]}\n<<<SNIPPET_END>>>\n\n"
            f"INSTRUCTIONS:\n"
            f"1. The examples provided are ANCHORS (e.g. clickable text), not the target value itself.\n"
            f"2. You must generate a regex that locates these anchors but CAPTURES the '{target_desc}' (e.g. href, src, id) associated with them.\n"
            f"3. Example: If target is 'URL' and anchor is 'Apply', regex might be: <a[^>]*href=\"([^\"]+)\"[^>]*>\\s*Apply\n"
            f"4. The regex must be generalized to work for similar items.\n\n"
            f"{_GENERATION_RULES}"
        )
    else:
        # Standard text extraction
        user = (
            f"TARGET: {target_desc}\n\n"
            f"EXAMPLES (the regex MUST match each of these exactly):\n{_examples_block(examples)}\n\n"
            f"CONTENT SNIPPET (generate a generalized regex that works on similar content):\n"
            f"<<<SNIPPET_START>>>\n{snippet[:32000]}\n<<<SNIPPET_END>>>\n\n"
            f"{_GENERATION_RULES}"
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
    fail = json.dumps(failures, ensure_ascii=False)
    
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

# ... (rest of validation code) ...

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
    raw = llm.chat(gen_messages, temperature=0.2)
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
        raw_ref = llm.chat(ref_messages, temperature=0.15)
        parsed_ref = _extract_json(raw_ref)
        pattern_ref = str(parsed_ref.get("regex", ""))
        flags_ref = str(parsed_ref.get("flags", ""))
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
