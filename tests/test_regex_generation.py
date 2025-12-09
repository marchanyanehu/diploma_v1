import json
from typing import Any, Dict

from shared import regex_generation as rg


class DummyLLM:
    """Deterministic stub that returns predefined JSON cycles.

    The first call returns an over-broad pattern, the second fixes it.
    """

    def __init__(self):
        self.calls = 0

    def chat(self, messages, temperature=0.0, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            # Over-broad: matches everything containing 'Job'
            return json.dumps(
                {
                    "regex": r"Other.+",  # matches wrong text
                    "flags": "i",
                    "extraction_mode": "findall",
                    "explanation": "wrong match",
                    "confidence": 0.4,
                }
            )
        # Refined: capture Job Title lines explicitly
        return json.dumps(
            {
                "regex": r"Job Title: ([A-Za-z ]+)",
                "flags": "",
                "extraction_mode": "group",
                "explanation": "Capture job title after label",
                "confidence": 0.7,
            }
        )


def test_validate_regex_basic_success():
    source = "Job Title: Senior Engineer\nOther\nJob Title: Data Scientist\n"
    examples = ["Senior Engineer", "Data Scientist"]
    pattern = r"Job Title: ([A-Za-z ]+)"
    result = rg.validate_regex(pattern, source, examples, flags="")
    assert result["success"], result
    assert set(result["distinct_matches"]) == {"Senior Engineer", "Data Scientist"}


def test_validate_regex_missing_example():
    source = "Job Title: Senior Engineer\nOther\nJob Title: Data Scientist\n"
    examples = ["Senior Engineer", "Data Scientist", "Product Manager"]
    pattern = r"Job Title: ([A-Za-z ]+)"
    result = rg.validate_regex(pattern, source, examples, flags="")
    assert not result["success"]
    assert "Product Manager" in result["missing_examples"]


def test_iterative_generation_refinement_flow():
    source = "Job Title: Senior Engineer\nOther text...\nJob Title: Data Scientist\n"
    examples = ["Senior Engineer", "Data Scientist"]
    llm = DummyLLM()
    outcome = rg.iterative_regex_generation(
        source=source,
        examples=examples,
        target_desc="job titles",
        llm=llm,
        max_iterations=3,
    )
    assert outcome["success"], outcome
    assert outcome["final_pattern"].startswith("Job Title:")
    # Ensure at least 2 attempts (initial + refinement)
    assert len(outcome["attempts"]) >= 2


def test_generation_messages_structure():
    snippet = "Some context Job Title: Senior Engineer etc"
    examples = ["Senior Engineer"]
    msgs = rg.build_generation_messages(snippet, examples, target_desc="job titles")
    assert msgs[0]["role"] == "system"
    assert any("EXAMPLES" in m["content"] for m in msgs if m["role"] == "user")


def test_refinement_messages_structure():
    prev = {"regex": "Job.+", "flags": "i", "extraction_mode": "findall", "explanation": "", "confidence": 0.1}
    failures: Dict[str, Any] = {"missing_examples": ["X"], "duplicate_ratio": 0.9}
    msgs = rg.build_refinement_messages(prev, failures, "snippet", ["X"], target_desc="jobs")
    assert msgs[0]["role"] == "system"
    assert any("REFINE" in m["content"] for m in msgs if m["role"] == "user")
