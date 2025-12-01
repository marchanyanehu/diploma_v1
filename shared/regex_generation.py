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

_SYSTEM_INSTRUCTION = (
    "You are a rigorous REGEX GENERATOR. You output ONLY strict JSON following the schema. "
    "Never include commentary, code fences, or additional text. Focus on precision and non-greedy, efficient patterns."
)

_EXTRA_DOMAIN_RULES = (
    "ADDITIONAL DOMAIN RULES (HTML & JSON):\n"
    "- Assume DOTALL ('.' matches newlines). Only add 's' flag if runtime requires; design pattern as if enabled.\n"
    "- NEVER wrap output in delimiters (no /regex/). Output raw pattern only.\n"
    "- ALWAYS escape literal curly braces when matching them: \\{ and \\}. Do NOT escape braces used for quantifiers.\n"
    "- HTML: Avoid binding to tag names (div, h1, a). Prefer stable class/id substrings.\n"
    "  * When anchoring on class attributes, omit volatile style-related fragments (e.g. size, animation tokens).\n"
    "  * After an anchored attribute, allow other attributes with [^>]*?\n"
    "  * Whitespace trimming: use \\s*+ (possessive if supported) or \\s*? lazily around optional spaces.\n"
    "  * For nested inline tags within the capture, skip them using (?:<[^>]+>)* non-greedily.\n"
    "  * To extract attribute values (e.g. href), bind a unique attribute sequence on the SAME tag.\n"
    "- JSON: Key matching should tightly bind the key token with surrounding punctuation and quotes.\n"
    "  * For potentially quoted content with internal quotes, use (.*?) non-greedy until the next unescaped quote.\n"
    "  * For nested objects, traverse minimally with [^}]*? or .*? depending on depth risk.\n"
    "  * Optional single value or list: (?:\\[\\s*)? before the first captured element.\n"
    "- Prefer a single capturing group that returns JUST the target value (no extra label text).\n"
)

_GENERATION_RULES = (
    "BASE RULES:\n"
    "1. Output ONLY JSON (no backticks).\n"
    "2. Use non-greedy quantifiers where possible. Avoid catastrophic backtracking ((.+)+, (.*)+, nested stars).\n"
    "3. Prefer explicit character classes over '.*' when context allows.\n"
    "4. Do NOT capture leading/trailing whitespace unless meaningful; trim with \\s*+ or \\s*?.\n"
    "5. Provide either: (a) a single capturing group containing the desired value (extraction_mode='group'), or (b) full-match items (extraction_mode='findall').\n"
    "6. Generalize variable segments with classes (\\d+, [A-Za-z]{2,}, [0-9A-F]{8}, etc.).\n"
    "7. Keep pattern length < 500 chars.\n"
    "8. Escape literal special characters (., +, ?, (, ), [, ], {, }, |, ^, $, /) when they must be matched verbatim.\n"
    "9. Flags: 'i' for case-insensitive only if examples differ by case; 'm' only if ^/$ anchors per line; 's' if required by engine.\n"
    "10. explanation <= 240 chars, concise.\n\n"
    + _EXTRA_DOMAIN_RULES
)

_JSON_EXAMPLE = (
    '{"regex": "Job\\s+Title: (?:[A-Z][A-Za-z]+(?:\\s+[A-Za-z]+)*)", "flags": "i", '
    '"extraction_mode": "findall", "explanation": "Capture job titles after the label", "confidence": 0.82}'
)


def _examples_block(examples: Sequence[str]) -> str:
    cleaned = [e.replace("\n", " ").strip() for e in examples if e.strip()]
    return "\n".join(f"- {c}" for c in cleaned[:10])  # cap examples for token economy


def build_generation_messages(snippet: str, examples: Sequence[str], *, target_desc: str) -> List[Dict[str, str]]:
    """Build chat messages for initial regex generation.

    Returns OpenAI-style messages list.
    """
    user = (
        f"TARGET: {target_desc}\n\n"
        f"EXAMPLES (the regex MUST match each):\n{_examples_block(examples)}\n\n"
        f"SNIPPET (context only, do NOT overfit to unrelated text):\n<<<SNIPPET_START>>>\n{snippet[:32000]}\n<<<SNIPPET_END>>>\n\n"
        f"Produce JSON with keys: regex, flags, extraction_mode, explanation, confidence.\n\n{_GENERATION_RULES}"
    )
    return [
        {"role": "system", "content": _SYSTEM_INSTRUCTION},
        {"role": "user", "content": user},
        {"role": "assistant", "content": _JSON_EXAMPLE},
    ]

def build_refinement_messages(
    previous_json: Dict[str, Any],
    failures: Dict[str, Any],
    snippet: str,
    examples: Sequence[str],
    *,
    target_desc: str,
) -> List[Dict[str, str]]:
    """Build chat messages for refinement (fix-it) prompt.

    previous_json: Parsed JSON from prior model attempt.
    failures: Output from validate_regex (subset describing issues).
    """
    prev = json.dumps(previous_json, ensure_ascii=False)
    fail = json.dumps(failures, ensure_ascii=False)
    user = (
        f"REFINE the previous regex so all examples match and issues are resolved.\n"
        f"TARGET: {target_desc}\n\n"
        f"EXAMPLES:\n{_examples_block(examples)}\n\n"
        f"SNIPPET:\n<<<SNIPPET_START>>>\n{snippet[:32000]}\n<<<SNIPPET_END>>>\n\n"
        f"PREVIOUS_REGEX_JSON: {prev}\n"
        f"VALIDATION_FAILURES: {fail}\n\n"
        "Return ONLY corrected JSON (same schema). Keep improvements minimal."
    )
    return [
        {"role": "system", "content": _SYSTEM_INSTRUCTION + " Focus now on *refinement* only."},
        {"role": "user", "content": user},
        {"role": "assistant", "content": _JSON_EXAMPLE},
    ]


# ------------------------------ Validation -------------------------------- #

_CATASTROPHIC_PATTERNS = [
    re.compile(r"\((?:\.\*|\.\+|\[.*?\]\*)\)+"),  # nested broad groups
    re.compile(r"(\(\.\*\)\+|\(\.\+\)\+)"),   # (.*)+ or (.+)+
]


@dataclass
class RegexValidationResult:
    success: bool
    matches: List[str]
    distinct_matches: List[str]
    missing_examples: List[str]
    too_many_matches: bool
    duplicate_ratio: float
    average_length: float
    issues: List[str]
    precision_proxy: float
    coverage_count: int
    coverage_ratio: float
    error: str | None
    flags_applied: str
    pattern: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "matches": self.matches,
            "distinct_matches": self.distinct_matches,
            "missing_examples": self.missing_examples,
            "too_many_matches": self.too_many_matches,
            "duplicate_ratio": self.duplicate_ratio,
            "average_length": self.average_length,
            "issues": self.issues,
            "precision_proxy": self.precision_proxy,
            "coverage_count": self.coverage_count,
            "coverage_ratio": self.coverage_ratio,
            "error": self.error,
            "flags_applied": self.flags_applied,
            "pattern": self.pattern,
        }


def _apply_flags(flags: str) -> int:
    flag_value = 0
    if not flags:
        return flag_value
    fset = set(flags.lower())
    if "i" in fset:
        flag_value |= re.IGNORECASE
    if "m" in fset:
        flag_value |= re.MULTILINE
    if "s" in fset:
        flag_value |= re.DOTALL
    return flag_value


def _likely_catastrophic(pattern: str) -> bool:
    for rx in _CATASTROPHIC_PATTERNS:
        if rx.search(pattern):  # pragma: no cover - defensive
            return True
    return False


def validate_regex(
    pattern: str,
    source: str,
    examples: Sequence[str],
    *,
    flags: str = "",
    max_matches: int = 200,
) -> Dict[str, Any]:
    """Validate regex pattern against source & examples.

    Returns dict suitable for logging & refinement logic.
    """
    # Helper for early failure returns with unified shape
    def _early_fail(err: str) -> Dict[str, Any]:
        missing = list(examples)
        issues: List[str] = ["missing_examples", "zero_matches"] if examples else ["zero_matches"]
        return RegexValidationResult(
            success=False,
            matches=[],
            distinct_matches=[],
            missing_examples=missing,
            too_many_matches=False,
            duplicate_ratio=0.0,
            average_length=0.0,
            issues=issues,
            precision_proxy=0.0,
            coverage_count=0,
            coverage_ratio=0.0,
            error=err,
            flags_applied=flags,
            pattern=pattern,
        ).to_dict()

    if not pattern:
        return _early_fail("empty pattern")

    if len(pattern) > 500:
        return _early_fail("pattern too long")

    if _likely_catastrophic(pattern):
        return _early_fail("potential catastrophic backtracking")

    try:
        compiled = re.compile(pattern, _apply_flags(flags))
    except re.error as exc:  # noqa: BLE001
        return _early_fail(f"compile_error: {exc}")

    matches: List[str] = []
    for i, m in enumerate(compiled.finditer(source)):
        if i >= max_matches:
            break
        # If there is a capturing group, prefer group(1) else full match
        if m.lastindex and m.lastindex >= 1:
            matches.append(m.group(1))
        else:
            matches.append(m.group(0))

    distinct = sorted({m for m in matches})
    missing = [ex for ex in examples if not any(ex in m for m in matches)]
    too_many = len(matches) >= max_matches
    duplicate_ratio = 1.0 - (len(distinct) / max(len(matches), 1)) if matches else 0.0
    avg_len = sum(len(m) for m in matches) / max(len(matches), 1) if matches else 0.0

    # Require capturing group if matches strictly wrap examples with constant prefix/suffix.
    has_group = bool(re.search(r"\([^?]", pattern))  # naive: any non-non-capturing paren
    if not has_group:
        # If every example is only a substring of some match but not equal to any distinct match, force refinement
        if examples and not any(ex in distinct for ex in examples):
            missing = list(examples)  # force failure path

    # Scoring / analytics
    total_distinct = len(distinct)
    matched_examples = len(examples) - len(missing) if examples else 0
    precision_proxy = (matched_examples / total_distinct) if total_distinct else 0.0
    coverage_count = matched_examples
    coverage_ratio = (matched_examples / len(examples)) if examples else 0.0

    # Issue classification
    issues: List[str] = []
    if not matches:
        issues.append("zero_matches")
    if missing:
        issues.append("missing_examples")
    if duplicate_ratio > 0.85:
        issues.append("excessive_duplicates")
    if avg_len > 2000:
        issues.append("over_broad_avg_length")

    success = (not issues) and (len(matches) > 0)

    return RegexValidationResult(
        success=success,
        matches=matches,
        distinct_matches=distinct,
        missing_examples=missing,
        too_many_matches=too_many,
        duplicate_ratio=duplicate_ratio,
        average_length=avg_len,
        issues=issues,
        precision_proxy=precision_proxy,
        coverage_count=coverage_count,
        coverage_ratio=coverage_ratio,
        error=None if success else (";".join(issues) if issues else None),
        flags_applied=flags,
        pattern=pattern,
    ).to_dict()


# -------------------------- Iterative Orchestration ------------------------ #

def _extract_json(raw: str) -> Dict[str, Any]:
    raw = raw.strip().strip("`")
    # Attempt direct parse then fallback to first {...}
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        try:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            pass
    return {}


def iterative_regex_generation(
    source: str,
    examples: Sequence[str],
    *,
    target_desc: str,
    llm: Any,
    max_iterations: int = 3,
    snippet: str | None = None,
) -> Dict[str, Any]:
    """Run iterative loop until success or exhaustion.

    Returns dict:
      {
        'success': bool,
        'attempts': [ { 'pattern': ..., 'validation': {...}, 'raw': '...' }, ...],
        'final_pattern': str | None,
        'final_flags': str | None,
      }
    """
    if not examples:
        return {"success": False, "error": "no examples"}
    # Ensure snippet_used is robust for JSON/large content
    snippet_used = snippet if snippet is not None and len(snippet) > 100 else source[:32000]
    attempts: List[Dict[str, Any]] = []

    gen_messages = build_generation_messages(snippet_used, examples, target_desc=target_desc)
    raw = llm.chat(gen_messages, temperature=0.2)
    parsed = _extract_json(raw)
    pattern = str(parsed.get("regex", ""))
    flags = str(parsed.get("flags", ""))
    val = validate_regex(pattern, source, examples, flags=flags)
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
        failures = {
            k: v
            for k, v in val.items()
            if k
            in {
                "missing_examples",
                "too_many_matches",
                "duplicate_ratio",
                "average_length",
                "issues",
                "precision_proxy",
                "coverage_count",
                "coverage_ratio",
                "error",
                "pattern",
            }
        }
        ref_messages = build_refinement_messages(prev, failures, snippet_used, examples, target_desc=target_desc)
        raw_ref = llm.chat(ref_messages, temperature=0.15)
        parsed_ref = _extract_json(raw_ref)
        pattern_ref = str(parsed_ref.get("regex", ""))
        flags_ref = str(parsed_ref.get("flags", ""))
        val_ref = validate_regex(pattern_ref, source, examples, flags=flags_ref)
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
