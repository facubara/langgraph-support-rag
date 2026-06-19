"""Gemini provider. The google-generativeai package is imported lazily so that mock
mode works without it installed."""

from __future__ import annotations

import time

from .base import LLMClient, LLMResponse


class GeminiLLM(LLMClient):
    def __init__(self, model: str, api_key: str) -> None:
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        import google.generativeai as genai  # lazy import

        genai.configure(api_key=api_key)
        self.model = model
        self._client = genai.GenerativeModel(model)

    def complete(self, system: str, prompt: str) -> LLMResponse:
        start = time.perf_counter()
        resp = self._client.generate_content(f"{system}\n\n{prompt}")
        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            text=getattr(resp, "text", ""),
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            latency_ms=latency_ms,
        )
