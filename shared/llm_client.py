"""
LLM Client abstraction powered by LiteLLM, configured for Baseten DeepSeek with
Gemini fallback.

This client provides a small, provider-agnostic interface for chat/completion
with built-in retries and timeouts, and reads configuration from environment
variables or the API settings module when available.

Environment variables:
  - LLM_PROVIDER (default: "baseten")
  - LLM_MODEL (default: "baseten/deepseek-ai/DeepSeek-V3.2")
  - LLM_FALLBACK_PROVIDER (default: "gemini")
  - LLM_FALLBACK_MODEL (default: "gemini-2.0-flash")
  - BASETEN_API_KEY: API key for Baseten-hosted DeepSeek
  - GOOGLE_API_KEY or GEMINI_API_KEY: API key for Google AI Studio (fallback)
  - LLM_REQUEST_TIMEOUT_S (default: 30)
  - LLM_MAX_RETRIES (default: 2)

Usage:
  from shared.llm_client import LLMClient
  client = LLMClient.from_env()
  text = client.generate_text("Summarize: ...")

Notes:
  - LiteLLM expects model names in the form "gemini/<model>" (e.g., gemini/gemini-2.0-flash)
  - LiteLLM expects Baseten model names prefixed with "baseten/" (e.g., baseten/deepseek-ai/DeepSeek-V3.2)
  - If you pass LLM_MODEL without the provider prefix, it will be added automatically.
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
DEFAULT_PROVIDER = "baseten"
DEFAULT_MODEL = "baseten/deepseek-ai/DeepSeek-V3.2"
DEFAULT_FALLBACK_PROVIDER = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
PROVIDER_MAX_TOKEN_LIMITS = {
    # Baseten DeepSeek returns 400s if max_tokens exceeds 262_144
    "baseten": 262_144,
}


def _resolve_model_name(provider: str, model: str) -> str:
    """Normalize model name for LiteLLM.

    For Gemini/AI Studio, LiteLLM expects names like: "gemini/gemini-2.0-flash".
    If the input is "gemini-2.5-flash", we prefix with "gemini/".
    If already prefixed (starts with "gemini/"), we return as-is.
    """
    provider_lower = provider.lower()
    if provider_lower == "gemini":
        return model if model.startswith("gemini/") else f"gemini/{model}"
    if provider_lower == "baseten":
        return model if model.startswith("baseten/") else f"baseten/{model}"
    # Future providers could be normalized here
    return model


def _clamp_max_tokens(provider: str, fallback_provider: Optional[str], max_tokens: Optional[int]) -> Optional[int]:
    """Clamp max_tokens to the lowest known provider limit to avoid BadRequest errors."""
    if max_tokens is None:
        return None

    limits: List[int] = []
    for p in (provider, fallback_provider):
        if not p:
            continue
        limit = PROVIDER_MAX_TOKEN_LIMITS.get(p.lower())
        if limit:
            limits.append(limit)

    if not limits:
        return max_tokens

    allowed = min(limits)
    if max_tokens > allowed:
        logger.warning(
            "Configured max_tokens=%s exceeds provider limit (%s); clamping to %s",
            max_tokens,
            allowed,
            allowed,
        )
        return allowed
    return max_tokens


@dataclass
class LLMClientConfig:
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    fallback_provider: str = DEFAULT_FALLBACK_PROVIDER
    fallback_model: str = DEFAULT_GEMINI_MODEL
    timeout_s: int = 30
    max_retries: int = 2
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    log_payloads: bool = False


class LLMClient:
    def __init__(self, config: LLMClientConfig):
        self.config = config
        self.model_name = _resolve_model_name(config.provider, config.model)
        self.fallback_model_name = (
            _resolve_model_name(config.fallback_provider, config.fallback_model)
            if config.fallback_model
            else None
        )
        self.has_fallback = bool(self.fallback_model_name)

        def _warn_missing_key(provider: str, label: str) -> None:
            provider_lower = provider.lower()
            if provider_lower == "gemini":
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                if not api_key:
                    logger.warning(
                        "No GOOGLE_API_KEY/GEMINI_API_KEY found; %s LLM calls will fail at runtime.",
                        label,
                    )
            elif provider_lower == "baseten":
                api_key = os.getenv("BASETEN_API_KEY")
                if not api_key:
                    logger.warning(
                        "No BASETEN_API_KEY found; %s LLM calls will fail at runtime.",
                        label,
                    )

        _warn_missing_key(config.provider, "primary")
        if self.has_fallback:
            _warn_missing_key(config.fallback_provider, "fallback")

    @classmethod
    def from_env(cls) -> "LLMClient":
        # Try to read from API settings if available
        provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)
        model = os.getenv("LLM_MODEL")
        if not model:
            try:
                # Lazy import to avoid cyclic deps in tests
                from services.api.config import settings  # type: ignore

                model = getattr(settings, "llm_model", DEFAULT_MODEL)
            except Exception:
                model = DEFAULT_MODEL

        fallback_provider = os.getenv("LLM_FALLBACK_PROVIDER")
        if not fallback_provider:
            try:
                from services.api.config import settings  # type: ignore

                fallback_provider = getattr(settings, "llm_fallback_provider", DEFAULT_FALLBACK_PROVIDER)
            except Exception:
                fallback_provider = DEFAULT_FALLBACK_PROVIDER

        fallback_model = os.getenv("LLM_FALLBACK_MODEL")
        if not fallback_model:
            try:
                from services.api.config import settings  # type: ignore

                fallback_model = getattr(settings, "llm_fallback_model", DEFAULT_GEMINI_MODEL)
            except Exception:
                fallback_model = DEFAULT_GEMINI_MODEL

        timeout_s = int(os.getenv("LLM_REQUEST_TIMEOUT_S", "30"))
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        max_tokens_env = os.getenv("LLM_MAX_TOKENS")
        max_tokens_raw = int(max_tokens_env) if max_tokens_env else None
        max_tokens = _clamp_max_tokens(provider, fallback_provider, max_tokens_raw)

        log_payloads = os.getenv("LLM_LOG_PAYLOADS", "false").lower() in {"1", "true", "yes"}
        cfg = LLMClientConfig(
            provider=provider,
            model=model,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            timeout_s=timeout_s,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
            log_payloads=log_payloads,
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

        def _run_with_retries(model_name: str, label: str) -> str:
            last_exc: Exception | None = None
            for attempt in range(retry_count + 1):
                try:
                    if self.config.log_payloads:
                        try:
                            logger.debug("LLM request payload (%s): %s", label, messages)
                        except Exception:
                            logger.debug("LLM request payload logging skipped (unserializable)")
                    resp = completion(
                        model=model_name,
                        messages=messages,
                        stream=False,  # ensure non-streaming response
                        **params,
                    )
                    text = self._extract_text_from_response(resp)
                    if self.config.log_payloads:
                        try:
                            logger.debug("LLM response text (%s): %s", label, text)
                        except Exception:
                            logger.debug("LLM response logging skipped (unserializable)")
                    return text
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt >= retry_count:
                        break
                    backoff = 0.5 * (attempt + 1)
                    logger.info(
                        "%s LLM retry %s/%s due to %s; backing off %.1fs",
                        label,
                        attempt + 1,
                        retry_count,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
            raise RuntimeError(f"{label} LLM request failed after {retry_count + 1} attempts: {last_exc}")

        try:
            return _run_with_retries(self.model_name, "primary")
        except Exception as primary_exc:
            if not self.has_fallback or not self.fallback_model_name:
                raise
            logger.info(
                "Primary LLM (%s) failed with %s; attempting fallback model %s",
                self.model_name,
                primary_exc,
                self.fallback_model_name,
            )
            try:
                return _run_with_retries(self.fallback_model_name, "fallback")
            except Exception as fallback_exc:
                raise RuntimeError(
                    "Primary and fallback LLM requests failed. "
                    f"Primary error: {primary_exc}; Fallback error: {fallback_exc}"
                )

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
