"""Tests for Task #405 snippet extraction utility."""
from __future__ import annotations

from shared.snippet_extractor import extract_snippet_around_example


SAMPLE_SOURCE = (
    "Header line about jobs\n"
    "Some unrelated intro text explaining context.\n"
    "Senior Python Developer - Remote Europe (Apply Now)\n"
    "Benefits: great culture, stock options, relocation support.\n"
    "Another trailing line with summary.\n"
)


def test_extract_snippet_found_basic():
    ex = "Senior Python Developer"
    res = extract_snippet_around_example(SAMPLE_SOURCE, ex, max_chars=200, line_radius=1)
    assert res["found"] is True
    assert ex.lower() in res["snippet"].lower()
    # Should include at most 3 lines (radius 1 => center + 1 each side)
    assert res["total_lines"] <= 3
    assert len(res["snippet"]) <= 200


def test_extract_snippet_not_found():
    res = extract_snippet_around_example(SAMPLE_SOURCE, "nonexistent phrase", max_chars=120)
    assert res["found"] is False
    assert len(res["snippet"]) <= 120


def test_extract_snippet_single_long_line_truncation():
    long_line = "A" * 1000
    res = extract_snippet_around_example(long_line, "AAAA", max_chars=80, line_radius=0)
    assert res["found"] is True
    assert res["truncated"] is True
    assert len(res["snippet"]) <= 85  # allow for ellipses
