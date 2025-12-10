"""Tests for Task #403 example finder."""
from __future__ import annotations

from services.ai_worker.example_finder import find_target_examples


def test_find_target_examples_basic():
    inner = """
Senior Python Developer
We are hiring Senior Python Engineers in Europe for remote positions.
Apply now for Python backend jobs.
Random line without signal.
""".strip()
    kws = ["senior", "python", "jobs"]
    examples = find_target_examples(inner, keywords=kws, target="job links", max_examples=3)
    assert examples, "Should return at least one example"
    # Ensure matched keywords subset logic works
    for ex in examples:
        assert any(k in ex["text"].lower() for k in kws)
        assert ex["matched_keywords"], "Matched keywords should not be empty"


def test_find_target_examples_empty():
    assert find_target_examples("", keywords=["a"]) == []
    assert find_target_examples("Some text", keywords=[]) == []
