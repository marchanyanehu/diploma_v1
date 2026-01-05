import json
import re
import html as html_lib
from pathlib import Path
from typing import Any, Dict

from services.ai_worker import regex_generation as rg


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
    # Need >50% missing to trigger failure
    examples = ["Senior Engineer", "Data Scientist", "Missing1", "Missing2", "Missing3"]
    pattern = r"Job Title: ([A-Za-z ]+)"
    result = rg.validate_regex(pattern, source, examples, flags="")
    assert not result["success"]
    assert "Missing1" in result["missing_examples"]


def test_generate_composite_regex_fallback_order_whitespace_mismatch():
    """Test that composite generation proceeds even if examples are not strictly locatable in source (e.g. whitespace diff)."""
    source = "Title:    Manager"
    examples = [{"job_title": "Title: Manager"}] # Exact string mismatch due to spaces
    
    class CompositeLLM:
        def chat(self, messages, temperature=0.0, **kwargs):
            # Return a regex that handles the extra spaces
            return json.dumps({
                "regex": r"(Title:\s+Manager)", 
                "flags": "",
                "confidence": 1.0
            })
            
    llm = CompositeLLM()
    # This calls generate_composite_regex which uses _find_example_position_in_source.
    # _find... will fail to find "Title: Manager" in "Title:    Manager".
    # Before the fix, this would return error "Could not locate...".
    # After the fix, it should log warning and proceed to use arbitrary order.
    result = rg.generate_composite_regex(
        source=source,
        examples=examples,
        target_desc="test",
        llm=llm
    )
    
    assert result["success"], f"Failed: {result.get('error')}"
    assert "job_title" in result["components"]



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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_regex_group1(pattern: str, content: str, *, flags: str = "s") -> list[str]:
    re_flags = 0
    if "i" in flags:
        re_flags |= re.IGNORECASE
    if "m" in flags:
        re_flags |= re.MULTILINE
    if "s" in flags:
        re_flags |= re.DOTALL

    rx = re.compile(pattern, re_flags)
    out: list[str] = []
    for m in rx.finditer(content):
        val = m.group(1) if (m.lastindex and m.lastindex >= 1) else m.group(0)
        if val is None:
            continue
        val = val.strip()
        if val:
            out.append(val)
    return out


def test_validate_regex_headless_html_titles_imentor_entities_ok():
    base = Path(__file__).parent / "htmls" / "imentor.org"
    html_content = _read_text(base / "tempo.html")
    pattern = _read_text(base / "job-titles-expected.txt").strip()

    # Simulate LLM examples: titles as visible text (entities decoded)
    raw_titles = _extract_regex_group1(pattern, html_content, flags="s")
    examples = [html_lib.unescape(t) for t in raw_titles][:3]

    result = rg.validate_regex(pattern, html_content, examples, flags="s")
    assert result["success"], result


def test_validate_regex_headless_html_titles_adcellerant_entities_ok():
    base = Path(__file__).parent / "htmls" / "adcellerant.com"
    html_content = _read_text(base / "tempo.html")
    pattern = _read_text(base / "job-titles-expected.txt").strip()

    raw_titles = _extract_regex_group1(pattern, html_content, flags="s")
    llm_like = [html_lib.unescape(t).strip() for t in raw_titles if t.strip()]

    # Ensure we include an entity-heavy example if present
    examples: list[str] = []
    examples.extend([t for t in llm_like if "&" in t][:1])
    examples.extend([t for t in llm_like if t not in examples][:2])

    assert len(examples) >= 2, "Need at least 2 examples for meaningful validation"
    result = rg.validate_regex(pattern, html_content, examples, flags="s")
    assert result["success"], result


class SnippetSensitiveLLM:
    """Returns a good regex only if the snippet includes the expected HTML anchor."""

    def __init__(self, *, expected_anchor_substring: str, good_json: dict, bad_json: dict):
        self.expected_anchor_substring = expected_anchor_substring
        self.good_json = good_json
        self.bad_json = bad_json
        self.calls = 0

    def chat(self, messages, temperature=0.0, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        joined = "\n".join(m.get("content", "") for m in messages)
        payload = self.good_json if self.expected_anchor_substring in joined else self.bad_json
        return json.dumps(payload)


def test_iterative_generation_auto_snippet_finds_examples_in_large_headless_html():
    # This HTML is large; without picking snippet around examples, we'd likely prompt only <head> content.
    base = Path(__file__).parent / "htmls" / "adcellerant.com"
    html_content = _read_text(base / "tempo.html")
    expected_pattern = _read_text(base / "job-titles-expected.txt").strip()

    raw_titles = _extract_regex_group1(expected_pattern, html_content, flags="s")
    examples = [html_lib.unescape(t).strip() for t in raw_titles if t.strip()][:3]
    assert examples, "No extracted examples from reference regex"

    llm = SnippetSensitiveLLM(
        expected_anchor_substring='class="elementor-heading-title adch1-heading',
        good_json={
            "regex": expected_pattern,
            "flags": "s",
            "extraction_mode": "group",
            "explanation": "reference pattern",
            "confidence": 0.9,
        },
        bad_json={
            "regex": r"THIS_WILL_NOT_MATCH_ANYTHING_12345",
            "flags": "s",
            "extraction_mode": "group",
            "explanation": "forcing failure when snippet is wrong",
            "confidence": 0.2,
        },
    )

    outcome = rg.iterative_regex_generation(
        source=html_content,
        examples=examples,
        target_desc="job titles",
        llm=llm,
        max_iterations=2,
        snippet=None,  # important: module must auto-pick a snippet around examples
    )
    assert outcome["success"], outcome
    assert outcome["final_pattern"] == expected_pattern


class AttributeRefineLLM:
    """First returns a regex that matches only CSS hrefs; then returns correct job-link regex."""

    def __init__(self, *, first_json: dict, second_json: dict):
        self.calls = 0
        self.first_json = first_json
        self.second_json = second_json

    def chat(self, messages, temperature=0.0, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        return json.dumps(self.first_json if self.calls == 1 else self.second_json)


def test_iterative_attribute_generation_requires_anchor_coverage_and_refines():
    base = Path(__file__).parent / "htmls" / "adcellerant.com"
    html_content = _read_text(base / "tempo.html")
    titles_pattern = _read_text(base / "job-titles-expected.txt").strip()
    links_pattern = _read_text(base / "job-links-expected.txt").strip()

    raw_titles = _extract_regex_group1(titles_pattern, html_content, flags="s")
    anchors = [html_lib.unescape(t).strip() for t in raw_titles if t.strip()][:3]
    assert len(anchors) >= 2

    llm = AttributeRefineLLM(
        first_json={
            # This matches only <link rel="stylesheet" href="...css"> in <head>, not near job titles.
            "regex": r'href="([^"]+?\.css)"',
            "flags": "s",
            "extraction_mode": "group",
            "explanation": "bad: css only",
            "confidence": 0.2,
        },
        second_json={
            "regex": links_pattern,
            "flags": "s",
            "extraction_mode": "group",
            "explanation": "capture job links",
            "confidence": 0.85,
        },
    )

    outcome = rg.iterative_regex_generation(
        source=html_content,
        examples=anchors,
        target_desc="job links (href)",
        llm=llm,
        max_iterations=3,
        is_attribute_extraction=True,
        snippet=None,
    )

    assert outcome["success"], outcome
    assert outcome["final_pattern"] == links_pattern
    assert len(outcome.get("attempts", [])) >= 2  # ensured refinement happened
