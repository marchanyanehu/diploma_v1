import os
import pytest

from shared.llm_client import LLMClient, _resolve_model_name


def test_resolve_model_name_gemini_prefix():
    assert _resolve_model_name("gemini", "gemini-2.0-flash") == "gemini/gemini-2.0-flash"
    assert _resolve_model_name("gemini", "gemini/gemini-2.0-flash") == "gemini/gemini-2.0-flash"


def test_client_from_env_defaults(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    client = LLMClient.from_env()
    # model_name should always be prefixed for gemini
    assert client.model_name.startswith("gemini/")


def test_client_warns_without_key(monkeypatch, caplog):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.0-flash")
    # Ensure no key present
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with caplog.at_level("WARNING"):
        _ = LLMClient.from_env()
    assert any("No GOOGLE_API_KEY" in r.message for r in caplog.records)

@pytest.mark.parametrize("raw_model,expected", [
    ("gemini-2.0-flash", "gemini/gemini-2.0-flash"),
    ("gemini/gemini-2.0-flash", "gemini/gemini-2.0-flash"),
])
def test_model_normalization(raw_model, expected):
    assert _resolve_model_name("gemini", raw_model) == expected
