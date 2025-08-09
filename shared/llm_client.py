"""
LLM Client abstraction powered by LiteLLM, configured for Google Gemini (AI Studio).

This client provides a small, provider-agnostic interface for chat/completion
with built-in retries and timeouts, and reads configuration from environment
variables or the API settings module when available.

Environment variables:
  - LLM_PROVIDER (default: "gemini"): currently only "gemini" is supported here
  - LLM_MODEL (default: "gemini-2.0-flash"): Gemini model name (e.g., gemini-2.5-flash)
  - GOOGLE_API_KEY or GEMINI_API_KEY: API key for Google AI Studio
  - LLM_REQUEST_TIMEOUT_S (default: 30)
  - LLM_MAX_RETRIES (default: 2)

Usage:
  from shared.llm_client import LLMClient
  client = LLMClient.from_env()
  text = client.generate_text("Summarize: ...")

Notes:
  - LiteLLM expects model names in the form "gemini/<model>" (e.g., gemini/gemini-2.0-flash)
  - If you pass LLM_MODEL without the "gemini/" prefix, it will be added automatically.
"""

from __future__ import annotations

import os
import time
import logging
from importlib import util as _il_util
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

if _il_util.find_spec("litellm") is not None:  # pragma: no cover - simple availability check
    from litellm import completion  # type: ignore
else:  # Fallback shim so import doesn't explode in test envs without litellm
    def completion(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError(
            "litellm is not installed. Install 'litellm' (e.g. pip install litellm) to enable real LLM calls."
        )


logger = logging.getLogger(__name__)
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def _resolve_model_name(provider: str, model: str) -> str:
    """Normalize model name for LiteLLM.

    For Gemini/AI Studio, LiteLLM expects names like: "gemini/gemini-2.0-flash".
    If the input is "gemini-2.5-flash", we prefix with "gemini/".
    If already prefixed (starts with "gemini/"), we return as-is.
    """
    if provider.lower() == "gemini":
        return model if model.startswith("gemini/") else f"gemini/{model}"
    # Future providers could be normalized here
    return model


@dataclass
class LLMClientConfig:
    provider: str = "gemini"
    model: str = DEFAULT_GEMINI_MODEL
    timeout_s: int = 30
    max_retries: int = 2
    temperature: float = 0.2
    max_tokens: Optional[int] = None


class LLMClient:
    def __init__(self, config: LLMClientConfig):
        self.config = config
        self.model_name = _resolve_model_name(config.provider, config.model)
        # Ensure API key is present for Gemini
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("No GOOGLE_API_KEY/GEMINI_API_KEY found; LLM calls will fail at runtime.")

    @classmethod
    def from_env(cls) -> "LLMClient":
        # Try to read from API settings if available
        provider = os.getenv("LLM_PROVIDER", "gemini")
        model = os.getenv("LLM_MODEL")
        if not model:
            try:
                # Lazy import to avoid cyclic deps in tests
                from services.api.config import settings  # type: ignore

                model = getattr(settings, "llm_model", DEFAULT_GEMINI_MODEL)
            except Exception:
                model = DEFAULT_GEMINI_MODEL

        timeout_s = int(os.getenv("LLM_REQUEST_TIMEOUT_S", "30"))
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        max_tokens_env = os.getenv("LLM_MAX_TOKENS")
        max_tokens = int(max_tokens_env) if max_tokens_env else None

        cfg = LLMClientConfig(
            provider=provider,
            model=model,
            timeout_s=timeout_s,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return cls(cfg)

    def _extract_text_from_response(self, resp: Any) -> str:
        """Extract text content from LiteLLM/OpenAI-like response objects."""
        # Unified small helpers
        def _as_dict(obj: Any) -> Dict[str, Any]:
            if isinstance(obj, dict):
                return obj
            try:
                return obj.__dict__  # type: ignore[attr-defined]
            except Exception:
                return {}

        # Try to get choices and message content
        try:
            d = _as_dict(resp)
            choices = d.get("choices") or getattr(resp, "choices", None)
            if not choices:
                return ""
            c0 = choices[0]
            c0d = _as_dict(c0)
            msg = c0d.get("message") or getattr(c0, "message", None) or {}
            md = _as_dict(msg)
            content = md.get("content") or getattr(msg, "content", None)
            if isinstance(content, list):
                return "".join(part.get("text", "") for part in content if isinstance(part, dict))
            return content or ""
        except Exception:
            return ""

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout_s: Optional[int] = None,
        retries: Optional[int] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a Chat Completions style request and return the content string.

        messages: OpenAI-style message list, e.g. [{"role":"system","content":"..."}, {"role":"user","content":"..."}]
        """
        temp = temperature if temperature is not None else self.config.temperature
        toks = max_tokens if max_tokens is not None else self.config.max_tokens
        to_s = timeout_s if timeout_s is not None else self.config.timeout_s
        retry_count = retries if retries is not None else self.config.max_retries
        params: Dict[str, Any] = {"temperature": temp, "timeout": to_s}
        if toks is not None:
            params["max_tokens"] = toks
        if extra_params:
            params.update(extra_params)

        last_exc: Exception | None = None
        for attempt in range(retry_count + 1):
            try:
                resp = completion(
                    model=self.model_name,
                    messages=messages,
                    stream=False,  # ensure non-streaming response
                    **params,
                )
                return self._extract_text_from_response(resp)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= retry_count:
                    break
                backoff = 0.5 * (attempt + 1)
                logger.info(
                    "LLM retry %s/%s due to %s; backing off %.1fs",
                    attempt + 1,
                    retry_count,
                    exc,
                    backoff,
                )
                time.sleep(backoff)
        raise RuntimeError(f"LLM request failed after {retry_count + 1} attempts: {last_exc}")

    def generate_text(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Convenience wrapper for single-prompt generation."""
        messages: List[Dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)
