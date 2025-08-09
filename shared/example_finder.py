"""Example Finder (Task #403)

Given page innerText and an intent structure (target, keywords), attempt to
locate representative example strings of the desired target data.

This step is heuristic-only (no extra LLM call) to produce concrete examples
we can later map back to network/HTML sources (#404) and provide as context
for regex generation (#405+#406).

Approach / Heuristics:
1. Normalize innerText into lines (strip, collapse spaces) keeping original line index.
2. Score each line based on the presence & density of keywords (case-insensitive).
3. Filter out lines that are too short/too long (configurable) or mostly punctuation.
4. Optionally split lines into tokens and attempt to extract sub-spans that contain
   at least one keyword plus surrounding context.
5. Return top-N distinct candidate strings plus metadata (line index, score, matched keywords).

Why this design:
- Fast and deterministic; avoids another LLM round-trip.
- Provides multiple candidates to improve resilience if some are noisy.
- Keeps metadata for later tracing back into the original sources.

Future enhancements (out of scope for Task #403 but documented):
- Use semantic similarity between the line and the 'target' phrase.
- Use regex templates for common target types (URLs, prices, emails, etc.).
- De-duplicate near-identical candidates via fuzzy hashing.

Public function contract:
find_target_examples(inner_text: str, *, keywords: list[str], target: str | None = None, max_examples: int = 5) -> list[dict]

Each dict has keys:
  text: str
  line_index: int
  score: float
  matched_keywords: list[str]
  char_start: int (offset within inner_text)  # approximate, start of line
  char_end: int   (offset within inner_text)  # approximate, end of line

Returns [] if nothing plausible found.

Edge cases handled:
- Empty inner_text or no keywords -> empty list.
- Duplicate lines or whitespace-only lines ignored.
- Very large pages: we cap processed lines for performance (FIRST 20k lines).
"""
from __future__ import annotations

from typing import List, Iterable, Iterator, TypedDict, Set
import math
import re

__all__ = ["find_target_examples"]

# Tunable constants (could later be pulled from config / env)
_MAX_LINES = 20_000
_MIN_LEN = 8        # minimal candidate length (after stripping)
_MAX_LEN = 240      # skip ultra-long lines to keep examples concise
_MIN_KEYWORD_DENSITY = 0.05  # matched_keyword_chars / line_len
_KEYWORD_SCORE = 2.0         # weight per distinct keyword
_CHAR_FRACTION_SCORE = 1.0   # weight for (matched_chars / len)
_LENGTH_PENALTY_EXP = 1.3    # exponent for length penalty scaling

_WS_RE = re.compile(r"\s+")
_PUNCT_ONLY_RE = re.compile(r"^[\W_]+$")


def _iter_lines(inner_text: str) -> Iterator[tuple[int, str, int, int]]:
    """Yield (line_index, raw_line, char_start, char_end) limited to _MAX_LINES.

    char_start/end are offsets within the original inner_text for approximate
    later mapping. We compute them via cumulative position scanning once.
    """
    if not inner_text:
        return []  # type: ignore[return-value]
    lines = inner_text.splitlines()
    out_count = 0
    pos = 0
    for idx, raw in enumerate(lines):
        if out_count >= _MAX_LINES:
            break
        line_len_with_sep = len(raw) + 1  # assume one separator (\n) except last
        char_start = pos
        char_end = pos + len(raw)
        pos += line_len_with_sep
        yield idx, raw, char_start, char_end
        out_count += 1


def _normalize(s: str) -> str:
    return _WS_RE.sub(" ", s.strip())


def _score_line(text: str, matched_keywords: List[str]) -> float:
    if not matched_keywords:
        return 0.0
    length = max(len(text), 1)
    distinct = len(set(matched_keywords))
    matched_chars = sum(len(k) for k in set(matched_keywords))
    density = matched_chars / length
    base = distinct * _KEYWORD_SCORE + density * _CHAR_FRACTION_SCORE
    # Penalize extremely short or very long lines smoothly
    length_penalty = math.pow(length / _MAX_LEN, _LENGTH_PENALTY_EXP) if length > _MAX_LEN else 1.0
    return base / length_penalty


class ExampleRecord(TypedDict):
    text: str
    line_index: int
    score: float
    matched_keywords: List[str]
    char_start: int
    char_end: int


def _candidate_from_line(norm: str, line_index: int, matched: List[str], cstart: int, cend: int) -> ExampleRecord | None:
    """Validate density + score and build ExampleRecord or None."""
    matched_chars = sum(len(m) for m in set(matched))
    if matched_chars / max(len(norm), 1) < _MIN_KEYWORD_DENSITY:
        return None
    sc = _score_line(norm, matched)
    if sc <= 0:
        return None
    return ExampleRecord(
        text=norm,
        line_index=line_index,
        score=float(f"{sc:.4f}"),
        matched_keywords=sorted(set(matched)),
        char_start=cstart,
        char_end=cend,
    )


def _valid_norm(norm: str) -> bool:
    if not norm:
        return False
    ln = len(norm)
    if ln < _MIN_LEN or ln > _MAX_LEN:
        return False
    if _PUNCT_ONLY_RE.match(norm):
        return False
    return True


def _keywords_in(lower_text: str, kw_set: Set[str]) -> List[str]:
    return [kw for kw in kw_set if kw in lower_text]

def find_target_examples(
    inner_text: str,
    *,
    keywords: List[str],
    target: str | None = None,
    max_examples: int = 5,
) -> List[ExampleRecord]:
    """Find representative example strings of target data based on keywords.

    Parameters:
        inner_text: Raw document.body.innerText captured earlier.
        keywords: Lowercased keyword tokens from intent extraction.
        target: Optional target noun phrase; currently used only for possible future weighting.
        max_examples: Maximum number of candidate examples to return.
    """
    if not inner_text or not keywords:
        return []

    kw_set = {k.lower() for k in keywords if k and len(k) <= 40}
    if not kw_set:
        return []

    candidates: List[ExampleRecord] = []
    seen_texts: Set[str] = set()

    for line_index, raw, cstart, cend in _iter_lines(inner_text):
        norm = _normalize(raw)
        if not _valid_norm(norm):
            continue
        low = norm.lower()
        if low in seen_texts:
            continue
        matched = _keywords_in(low, kw_set)
        if not matched:
            continue
        cand = _candidate_from_line(norm, line_index, matched, cstart, cend)
        if not cand:
            continue
        seen_texts.add(low)
        candidates.append(cand)

    if not candidates:
        return []

    # Sort by score descending, then by shorter length for readability
    candidates.sort(key=lambda d: (-float(d["score"]), len(d["text"])))

    # Truncate
    top = candidates[: max_examples]

    return top
