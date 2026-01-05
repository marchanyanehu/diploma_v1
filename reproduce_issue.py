
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath('.'))

from services.ai_worker.regex_generation import iterative_regex_generation, validate_regex
import re

class MockLLM:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
    
    def chat(self, messages, temperature=0.2, extra_params=None):
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp

# Case 1: Multiple fields (schema extraction)
# We want to see if it generates named groups
source = """
<div class="job">
  <h3>Senior Software Engineer</h3>
  <a href="/jobs/123">View Job</a>
</div>
<div class="job">
  <h3>Product Manager</h3>
  <a href="/jobs/456">View Job</a>
</div>
"""

examples = [
    "job_title: Senior Software Engineer | job_link: /jobs/123",
    "job_title: Product Manager | job_link: /jobs/456"
]

target_desc = "Extract items with fields: job_title, job_link. IMPORTANT: Use NAMED capturing groups for each field (e.g. (?P<field_name>...))"

# Mock LLM response WITHOUT groups to see if validation catches it
bad_response = '{"regex": "<h3>([^<]+)</h3>\\\\s*<a href=\\\"([^\\\"]+)\\\">", "flags": "s", "extraction_mode": "group", "explanation": "no named groups", "confidence": 0.8}'

llm = MockLLM([bad_response, bad_response, bad_response])

expected_fields = ["job_title", "job_link"]

print("--- Running validation for regex WITHOUT named groups ---")
val = validate_regex(
    "<h3>([^<]+)</h3>\\s*<a href=\"([^\"]+)\">", 
    source, 
    examples, 
    flags="s", 
    expected_fields=expected_fields
)
print(f"Success: {val['success']}")
print(f"Issues: {val['issues']}")

# Case 2: Intent extraction promotion
from services.ai_worker.intent_extraction import _coerce_schema

print("\n--- Testing intent extraction promotion ---")
intent_data = {
    "target": "jobs",
    "keywords": ["job titles", "job links"],
    "schema_fields": [],
    "confidence": 0.9
}
coerced = _coerce_schema(intent_data, "job titles and job links")
print(f"Coerced schema_fields: {coerced['schema_fields']}")
