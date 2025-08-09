"""Snippet Extraction Utility (Task #405)

Given a source string (e.g., HTML, JSON, plain text) and an example string that
was previously identified as representative target data, extract a *small*
contextual snippet suitable to send to an LLM for regex / pattern generation.

Design goals:
- Deterministic, lightweight (no extra LLM calls here).
- Keeps the example fully intact (never truncates inside the example span).
- Bounded size (default <= 600 chars) to control token usage.
- Prefers whole-line boundaries for readability (line radius heuristic).
- Graceful fallback if the example is not found (returns a head slice).

Public function contract:
extract_snippet_around_example(source: str, example: str, *, max_chars: int = 600, line_radius: int = 2, case_insensitive: bool = True) -> dict

Return dict keys:
  snippet: str            # The extracted snippet (trimmed, no leading/trailing blank lines)
  example: str            # Echo of the input example
  found: bool             # Whether the example was located in the source
  line_index: int | None  # Line index containing example, else None
  start_char: int         # Start offset in original source of snippet
  end_char: int           # End offset (exclusive) in original source of snippet
  total_lines: int        # Number of lines in snippet
  truncated: bool         # Whether we had to truncate due to max_chars

Edge cases handled:
- Empty source / example => returns minimal fallback snippet.
- Example not found => returns first max_chars slice with found=False.
- Extremely long lines => truncated around the example with ellipses where needed.

Heuristics:
1. Locate first occurrence (case-insensitive by default).
2. Map to line structure (splitlines). Track cumulative offsets for mapping.
3. Expand line window by `line_radius` on each side.
4. If resulting snippet > max_chars, iteratively reduce radius; if still too big,
   trim equally from start/end outside the example span.
5. Preserve readability: we prefer not to cut inside the example. If cuts are
   required, we add '…' at the trimmed edge(s).

Future enhancements (not in scope now):
- Token-aware trimming (preserve JSON structural boundaries or HTML tags).
- Multi-occurrence handling (choose highest-scoring occurrence by keyword density).
- Highlight markup for downstream UI rendering.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

__all__ = ["extract_snippet_around_example"]


@dataclass
class _LineInfo:
    index: int
    text: str
    start: int  # inclusive char offset in source
    end: int    # exclusive char offset in source


def _build_lines(source: str) -> List[_LineInfo]:
    lines_raw = source.splitlines(keepends=True)
    lines: List[_LineInfo] = []
    pos = 0
    for i, raw in enumerate(lines_raw):
        start = pos
        end = pos + len(raw)
        lines.append(_LineInfo(i, raw, start, end))
        pos = end
    # Ensure a trailing line if source does not end with newline
    if source and (not source.endswith("\n") and (not lines or lines[-1].text.endswith("\n") is False)):
        # Already accounted by splitlines(keepends=True); nothing extra needed.
        pass
    return lines


def _find_occurrence(source: str, example: str, case_insensitive: bool) -> Optional[Tuple[int, int]]:
    if not source or not example:
        return None
    if case_insensitive:
        low_s = source.lower()
        low_e = example.lower()
        idx = low_s.find(low_e)
    else:
        idx = source.find(example)
    if idx == -1:
        return None
    return idx, idx + len(example)


def _lines_span_for_occurrence(lines: List[_LineInfo], occ: Tuple[int, int]) -> Optional[int]:
    start, _ = occ
    for li in lines:
        if li.start <= start < li.end:
            return li.index
    return None


def extract_snippet_around_example(
    source: str,
    example: str,
    *,
    max_chars: int = 600,
    line_radius: int = 2,
    case_insensitive: bool = True,
) -> Dict[str, object]:
    """Extract a bounded snippet of source content around an example.

    See module docstring for detailed behavior.
    """
    if max_chars <= 50:  # enforce sane floor
        max_chars = 50
    if line_radius < 0:
        line_radius = 0

    if not source.strip():
        snippet = source[:max_chars]
        return {
            "snippet": snippet,
            "example": example,
            "found": False,
            "line_index": None,
            "start_char": 0,
            "end_char": len(snippet),
            "total_lines": snippet.count("\n") + 1 if snippet else 0,
            "truncated": len(snippet) < len(source),
        }

    occ = _find_occurrence(source, example, case_insensitive)
    lines = _build_lines(source)

    if not occ:
        # Fallback: first slice
        slice_text = source[:max_chars].rstrip()
        return {
            "snippet": slice_text,
            "example": example,
            "found": False,
            "line_index": None,
            "start_char": 0,
            "end_char": len(slice_text),
            "total_lines": slice_text.count("\n") + 1,
            "truncated": len(slice_text) < len(source),
        }

    occ_start, occ_end = occ
    occ_line_index = _lines_span_for_occurrence(lines, occ)

    if occ_line_index is None:  # Defensive fallback
        slice_text = source[:max_chars].rstrip()
        return {
            "snippet": slice_text,
            "example": example,
            "found": False,
            "line_index": None,
            "start_char": 0,
            "end_char": len(slice_text),
            "total_lines": slice_text.count("\n") + 1,
            "truncated": len(slice_text) < len(source),
        }

    # Initial window by line radius
    start_line = max(0, occ_line_index - line_radius)
    end_line = min(len(lines) - 1, occ_line_index + line_radius)

    def build_window(sl: int, el: int) -> Tuple[str, int, int, int]:
        seg_lines = lines[sl : el + 1]
        seg_start = seg_lines[0].start
        seg_end = seg_lines[-1].end
        text = source[seg_start:seg_end]
        return text, seg_start, seg_end, len(seg_lines)

    snippet_text, seg_start, seg_end, seg_line_count = build_window(start_line, end_line)

    # If snippet too large, reduce radius iteratively
    radius = line_radius
    while len(snippet_text) > max_chars and radius > 0:
        radius -= 1
        start_line = max(0, occ_line_index - radius)
        end_line = min(len(lines) - 1, occ_line_index + radius)
        snippet_text, seg_start, seg_end, seg_line_count = build_window(start_line, end_line)

    truncated = False

    # If still too large (e.g., single very long line), trim around occurrence
    if len(snippet_text) > max_chars:
        truncated = True
        # compute relative offsets inside snippet
        rel_occ_start = occ_start - seg_start
        rel_occ_end = occ_end - seg_start
        # Keep half budget on each side if possible
        budget = max_chars
        occ_len = rel_occ_end - rel_occ_start
        if occ_len > budget:  # pathological (example itself longer than max)
            # Take the middle slice of the example
            middle_start = rel_occ_start
            snippet_text = snippet_text[middle_start : middle_start + budget]
            seg_start = occ_start
            seg_end = occ_start + len(snippet_text)
        else:
            side_budget = (budget - occ_len) // 2
            left_start = max(0, rel_occ_start - side_budget)
            right_end = min(len(snippet_text), rel_occ_end + side_budget)
            # Adjust if we have spare due to reaching boundaries
            current_len = right_end - left_start
            if current_len < budget:
                remaining = budget - current_len
                # Try extend right first
                extend_right = min(remaining, len(snippet_text) - right_end)
                right_end += extend_right
                remaining -= extend_right
                if remaining > 0:
                    left_start = max(0, left_start - remaining)
            trimmed = snippet_text[left_start:right_end]
            # Add ellipses if we cut
            if left_start > 0:
                trimmed = "…" + trimmed
                seg_start += left_start  # shift start
            if right_end < len(snippet_text):
                trimmed = trimmed + "…"
                seg_end = seg_start + (right_end - left_start)
            snippet_text = trimmed

    # Final clean-up: strip leading/trailing blank lines
    snippet_clean = "\n".join([ln for ln in snippet_text.splitlines() if ln.strip()])

    return {
        "snippet": snippet_clean,
        "example": example,
        "found": True,
        "line_index": occ_line_index,
        "start_char": seg_start,
        "end_char": seg_end,
        "total_lines": seg_line_count,
        "truncated": truncated or len(snippet_clean) < len(snippet_text),
    }
