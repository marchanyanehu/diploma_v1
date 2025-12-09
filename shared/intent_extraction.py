"""Intent Extraction Module (Task #402)

Provides a prompt engineering template and helper to turn a user's free-form
request into a structured intent JSON object. Uses the shared LLMClient.

Design goals:
- Deterministic JSON output (no prose) with strict schema.
- Graceful fallback if LLM unavailable (returns minimal structure).
- Easy to extend with new fields without breaking callers.

Expected JSON schema (initial version):
{
  "target": str,                 # High-level entity / object user wants (e.g., "job links")
  "original_input": str,         # Raw user prompt
  "keywords": [str],             # Key search terms / filters
  "constraints": [str],          # Optional constraints (e.g., location, salary, date)
  "output_shape": str,           # Short summary of desired output (e.g., "list of URLs")
  "confidence": float            # 0-1 self-assessed confidence
}

Environment overrides:
  INTENT_MODEL (default: value from LLM_MODEL or fallback)

Usage:
  from shared.intent_extraction import extract_intent
  intent = extract_intent("i want to have jobs scraped here for remote python roles in europe")
"""
from __future__ import annotations

import json
import os
import re
import logging
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient
from shared.prompts import INTENT_EXTRACTION_SYSTEM_PROMPT, INTENT_EXTRACTION_USER_TEMPLATE

logger = logging.getLogger(__name__)



_JSON_FALLBACK_TEMPLATE = {
    "target": "",
    "original_input": "",
    "keywords": [],
    "constraints": [],
    "output_shape": "",
    "confidence": 0.0,
    "source_type": "text",
    "target_attribute": None,
    "schema_fields": [],
}

_JSON_EXAMPLE = (
    '{"target": "job details", "original_input": "job_title, country, city, state, apply_url", '
    '"keywords": ["job_title", "country", "city", "state", "apply_url"], "constraints": [], '
    '"output_shape": "structured JSON with named fields", "confidence": 0.95, '
    '"source_type": "text", "target_attribute": null, '
    '"schema_fields": ["job_title", "country", "city", "state", "apply_url"]}'
)

_DEFENSIVE_JSON_REGEX = re.compile(r"\{.*\}", re.DOTALL)


def _build_messages(user_input: str) -> List[Dict[str, Any]]:
    return [
        {"role": "system", "content": INTENT_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": INTENT_EXTRACTION_USER_TEMPLATE.format(user_input=user_input)},
        {"role": "assistant", "content": _JSON_EXAMPLE},  # few-shot style clarification
        {"role": "user", "content": user_input},
    ]


def _safe_parse_json(raw: str, original: str) -> Dict[str, Any]:
    """Attempt to parse a JSON object from raw model output; fallback gracefully."""
    text = raw.strip()
    if not text:
        return {**_JSON_FALLBACK_TEMPLATE, "original_input": original}
    # Try direct
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return _coerce_schema(data, original)
    except Exception:
        pass
    # Try to isolate first JSON object substring
    match = _DEFENSIVE_JSON_REGEX.search(text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return _coerce_schema(data, original)
        except Exception:
            pass
    return {**_JSON_FALLBACK_TEMPLATE, "original_input": original}


def _dedupe_lower(seq: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in seq:
        if not item:
            continue
        low = item.lower().strip()
        if low not in seen:
            seen.add(low)
            out.append(low)
    return out


def _coerce_schema(data: Dict[str, Any], original: str) -> Dict[str, Any]:
    # Extract schema_fields - these are the exact field names for output
    schema_fields = [str(x).strip() for x in data.get("schema_fields", []) if x][:20]
    
    # If no schema_fields but keywords look like field names (snake_case or single words), use them
    keywords = _dedupe_lower([str(x) for x in data.get("keywords", [])][:30])
    if not schema_fields and keywords:
        # Check if keywords look like field names (contain _ or are single technical words)
        potential_fields = [k for k in keywords if '_' in k or k in ['country', 'city', 'state', 'title', 'url', 'name', 'price', 'description']]
        if len(potential_fields) >= 2:
            schema_fields = potential_fields
    
    return {
        "target": str(data.get("target", ""))[:100].strip(),
        "original_input": original,
        "keywords": keywords,
        "constraints": [str(x).strip() for x in data.get("constraints", [])][:30],
        "output_shape": str(data.get("output_shape", ""))[:120].strip(),
        "confidence": _safe_confidence(data.get("confidence", 0.0)),
        "source_type": str(data.get("source_type", "text")).lower(),
        "target_attribute": str(data.get("target_attribute", "") or "") or None,
        "schema_fields": schema_fields,
    }


def _safe_confidence(val: Any) -> float:
    try:
        f = float(val)
        if f < 0:
            return 0.0
        if f > 1:
            return 1.0
        return f
    except Exception:
        return 0.5


def extract_intent(user_input: str, *, llm: Optional[Any] = None) -> Dict[str, Any]:
    """Extract structured intent from user_input using the LLM.

    If the LLM fails or no key is configured, returns a minimal fallback.
    """
    if not user_input.strip():
        return {**_JSON_FALLBACK_TEMPLATE, "original_input": user_input}

    client = llm or LLMClient.from_env()
    messages = _build_messages(user_input)

    try:
        raw = client.chat(messages, temperature=0.1, extra_params={"response_format": {"type": "json_object"}})
        parsed = _safe_parse_json(raw, user_input)
        return parsed
    except Exception as exc:  # noqa: BLE001
        logger.warning("Intent extraction failed: %s", exc)
        return {**_JSON_FALLBACK_TEMPLATE, "original_input": user_input}


__all__ = ["extract_intent"]
