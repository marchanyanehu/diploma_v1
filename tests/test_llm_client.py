import os
import pytest

from shared.llm_client import LLMClient, _resolve_model_name


def test_resolve_model_name_prefixes():
    assert _resolve_model_name("gemini", "gemini-2.0-flash") == "gemini/gemini-2.0-flash"
    assert _resolve_model_name("gemini", "gemini/gemini-2.0-flash") == "gemini/gemini-2.0-flash"
    assert _resolve_model_name("baseten", "deepseek-ai/DeepSeek-V3.2") == "baseten/deepseek-ai/DeepSeek-V3.2"
    assert (
        _resolve_model_name("baseten", "baseten/deepseek-ai/DeepSeek-V3.2")
        == "baseten/deepseek-ai/DeepSeek-V3.2"
    )


def test_client_from_env_defaults(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_FALLBACK_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_FALLBACK_MODEL", raising=False)
    # Avoid warning noise in test logs
    monkeypatch.setenv("BASETEN_API_KEY", "test-primary")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-fallback")
    client = LLMClient.from_env()
    # model_name should always be prefixed for baseten defaults
    assert client.model_name.startswith("baseten/")
    assert client.fallback_model_name is not None
    assert client.fallback_model_name.startswith("gemini/")


def test_client_warns_without_key(monkeypatch, caplog):
    monkeypatch.setenv("LLM_PROVIDER", "baseten")
    monkeypatch.setenv("LLM_MODEL", "baseten/deepseek-ai/DeepSeek-V3.2")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "gemini-2.0-flash")
    # Ensure no keys present
    monkeypatch.delenv("BASETEN_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with caplog.at_level("WARNING"):
        _ = LLMClient.from_env()
    assert any("No BASETEN_API_KEY" in r.message for r in caplog.records)
    assert any("No GOOGLE_API_KEY" in r.message for r in caplog.records)

def test_chat_uses_fallback_when_primary_fails(monkeypatch):
    calls = []

    def fake_completion(model, messages, stream, **params):
        calls.append(model)
        if model.startswith("baseten/"):
            raise RuntimeError("primary down")
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr("shared.llm_client.completion", fake_completion)
    monkeypatch.setenv("LLM_PROVIDER", "baseten")
    monkeypatch.setenv("LLM_MODEL", "baseten/deepseek-ai/DeepSeek-V3.2")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("BASETEN_API_KEY", "primary-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "fallback-key")
    client = LLMClient.from_env()

    text = client.chat([{"role": "user", "content": "hi"}])

    assert text == "ok"
    assert calls[0].startswith("baseten/deepseek-ai/DeepSeek-V3.2")
    assert calls[-1].startswith("gemini/gemini-2.0-flash")
