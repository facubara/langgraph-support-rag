"""Build the configured LLM client and wrap it with retry / timeout / fallback."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

from ..config import settings
from .base import LLMClient, LLMResponse
from .mock import MockLLM


def build_client(provider: str, model: str, api_key: str) -> LLMClient:
    if provider == "mock":
        return MockLLM(model="mock-llm")
    if provider == "gemini":
        from .gemini import GeminiLLM

        return GeminiLLM(model=model, api_key=api_key)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")


class ResilientLLM(LLMClient):
    """Adds bounded retries, a per-call timeout, and an optional fallback model."""

    def __init__(
        self,
        primary: LLMClient,
        fallback: LLMClient | None = None,
        max_retries: int = 2,
        timeout: float = 30.0,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.max_retries = max_retries
        self.timeout = timeout
        self.model = primary.model

    def _call(self, client: LLMClient, system: str, prompt: str) -> LLMResponse:
        # ThreadPoolExecutor.result(timeout=) is cross-platform (works on Windows,
        # unlike signal-based timeouts).
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(client.complete, system, prompt).result(timeout=self.timeout)

    def complete(self, system: str, prompt: str) -> LLMResponse:
        last_err: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                return self._call(self.primary, system, prompt)
            except Exception as err:  # noqa: BLE001 - record and retry/fallback
                last_err = err
        if self.fallback is not None:
            try:
                return self._call(self.fallback, system, prompt)
            except Exception as err:  # noqa: BLE001
                last_err = err
        raise RuntimeError(f"LLM call failed after retries and fallback: {last_err}")

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        # Retry / fall back only *before the first token* — once tokens are on the wire we
        # can't un-send them, so a mid-stream failure must propagate to the caller (the
        # streaming endpoint surfaces it as an SSE `error` event).
        last_err: Exception | None = None
        for _ in range(self.max_retries + 1):
            emitted = False
            try:
                for chunk in self.primary.stream(system, prompt):
                    emitted = True
                    yield chunk
                return
            except Exception as err:  # noqa: BLE001
                last_err = err
                if emitted:
                    raise
        if self.fallback is not None:
            yield from self.fallback.stream(system, prompt)
            return
        raise RuntimeError(f"LLM stream failed after retries and fallback: {last_err}")


def get_llm() -> LLMClient:
    # In replay mode, serve the original run's recorded completions instead of calling a
    # provider — this is what makes a replayed conversation deterministic.
    from ..replay import ReplayLLM, active_replay

    recorded = active_replay()
    if recorded is not None:
        return ReplayLLM(recorded)

    primary = build_client(settings.llm_provider, settings.llm_model, settings.google_api_key)
    fallback: LLMClient | None = None
    if settings.llm_fallback_model and settings.llm_provider != "mock":
        fallback = build_client(
            settings.llm_provider, settings.llm_fallback_model, settings.google_api_key
        )
    return ResilientLLM(
        primary,
        fallback,
        max_retries=settings.llm_max_retries,
        timeout=settings.llm_timeout_seconds,
    )
