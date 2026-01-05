
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from services.ai_worker import css_selector_generation

# Mock LLM that returns a fixed selector
class MockLLM:
    def __init__(self, expected_selector="a.job-link"):
        self.expected_selector = expected_selector
        self.received_snippet = ""

    def chat(self, messages, temperature=0.2):
        user_msg = messages[1]['content']
        match = re.search(r"HTML SNIPPET:\n(.*)\n\nGenerate", user_msg, re.DOTALL)
        if match:
            self.received_snippet = match.group(1)
        
        return json.dumps({
            "selector": self.expected_selector,
            "attribute": "href",
            "explanation": "Mocked response"
        })

def test_generate_css_selector_snippet_robustness():
    # Use real HTML file from test resources
    base_dir = Path(__file__).parent / "htmls" / "adcellerant.com"
    html_path = base_dir / "tempo.html"
    if not html_path.exists():
        pytest.skip(f"Test resource {html_path} not found")

    html_content = html_path.read_text(encoding='utf-8', errors='ignore')
    
    # Define examples: First one is BOGUS (not in HTML), Second one is REAL
    examples = [
        "https://this-url-does-not-exist.com/foo",
        "https://adcellerant.com/careers-job-listing/co/engineering/78.264/engineering-manager/all"
    ]
    
    # We want to verify that the snippet sent to LLM contains the REAL example,
    # meaning the code correctly skipped the first bogus example and used the second one to locate the snippet.
    
    llm = MockLLM()
    
    # We don't care about the result of the generation (since we mock the LLM response)
    # We only care about what the LLM received.
    # Note: We must ensure parsel is mocked or present.
    
    with patch("services.ai_worker.css_selector_generation.Selector") as mock_selector:
        # Mock validation to pass so we don't retry loop
        mock_selector_instance = mock_selector.return_value
        mock_selector_instance.css.return_value.getall.return_value = examples # Pretend we found them
        
        result = css_selector_generation.generate_css_selector(
            html_content=html_content,
            examples=examples,
            target_desc="job link",
            llm=llm,
            max_retries=0 # 1 attempt
        )
        
        # Check snippet
        snippet = llm.received_snippet
        assert snippet, "LLM received empty snippet"
        assert examples[1] in snippet, "Valid example NOT found in snippet! Fallback logic failed."
        assert examples[0] not in snippet, "Bogus example found in snippet? Impossible."

def test_get_snippet_logic():
    # Unit test for _get_snippet specifically
    html = "<html><body><p>foo</p><p>bar &amp; baz</p></body></html>"
    examples = ["missing", "bar & baz"] # "bar & baz" is in HTML as "bar &amp; baz"
    
    snippet = css_selector_generation._get_snippet(html, examples)
    
    # Should contain "bar &amp; baz"
    assert "bar &amp; baz" in snippet
    assert len(snippet) < len(html) + 100 # just checking it didn't crash

