"""Unit tests for intent extraction (Task #402).

We mock the LLMClient to ensure deterministic behavior without real API calls.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from shared.intent_extraction import extract_intent


class DummyLLM:
    def __init__(self, responses: List[str]):
        self._responses = responses
        self._i = 0

    def chat(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        if self._i >= len(self._responses):
            raise RuntimeError("No more dummy responses")
        r = self._responses[self._i]
        self._i += 1
        return r


def test_extract_intent_basic():
    dummy_json = (
        '{"target": "job links", "original_input": "IGNORED", '
        '"keywords": ["Senior", "Python", "Jobs", "Python"], '
        '"constraints": ["remote", "europe"], '
        '"output_shape": "list of job urls", "confidence": 0.85}'
    )
    llm = DummyLLM([dummy_json])
    result = extract_intent(
        "I want senior Python jobs remote in Europe", llm=llm
    )
    assert result["target"] == "job links"
    assert result["original_input"].startswith("I want senior Python")
    assert sorted(result["keywords"]) == sorted(["senior", "python", "jobs"])
    assert "remote" in result["constraints"] and "europe" in result["constraints"]
    assert 0 <= result["confidence"] <= 1


def test_extract_intent_fallback_on_bad_json():
    llm = DummyLLM(["not json :: just text"])
    result = extract_intent("just something", llm=llm)
    assert result["original_input"] == "just something"
    assert result["target"] == ""
    assert result["keywords"] == []


def test_extract_intent_empty_input():
    llm = DummyLLM(["{}"])
    result = extract_intent("   ", llm=llm)
    assert result["original_input"].strip() == ""
    assert result["keywords"] == []
