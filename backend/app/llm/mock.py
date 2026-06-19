"""Deterministic mock LLM so the full pipeline runs with no API key and zero cost."""

from __future__ import annotations

import time
from collections.abc import Iterator

from ..config import settings
from .base import LLMClient, LLMResponse


class MockLLM(LLMClient):
    def __init__(self, model: str = "mock-llm") -> None:
        self.model = model

    def complete(self, system: str, prompt: str) -> LLMResponse:
        start = time.perf_counter()
        text = self._respond(prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            cost_usd=0.0,
            latency_ms=latency_ms,
        )

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        # Emit word-sized chunks so the demo visibly streams with no API key. The
        # concatenation equals `complete()`'s text exactly, which keeps replay consistent.
        text = self._respond(prompt)
        for i, word in enumerate(text.split(" ")):
            yield word if i == 0 else " " + word
            if settings.mock_stream_delay:
                time.sleep(settings.mock_stream_delay)

    @staticmethod
    def _respond(prompt: str) -> str:
        p = prompt.lower()
        if "duplicate" in p:
            return (
                "[mock] I see a potential duplicate charge on your account. I'd verify it "
                "against your invoice history before issuing any refund."
            )
        if "refund" in p:
            return (
                "[mock] Based on the refund policy and your invoice history, here is how I'd "
                "assess your refund eligibility."
            )
        if "cancel" in p:
            return "[mock] Here are the steps to cancel and what happens to your billing."
        return "[mock] Thanks for reaching out — here is what I found for your request."
