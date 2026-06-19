"""LLM client interface and response type shared by every provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """A single completion plus the metadata the trace/eval layers need."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient(ABC):
    """Every provider implements `complete(system, prompt) -> LLMResponse`."""

    model: str

    @abstractmethod
    def complete(self, system: str, prompt: str) -> LLMResponse:  # pragma: no cover - interface
        ...

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        """Yield the completion in text chunks.

        Default: one chunk holding the whole `complete()` text — so every provider, the
        resilience wrapper, and the replay client are stream-capable for free, and replay
        stays deterministic. Providers override this for true token streaming.
        """
        yield self.complete(system, prompt).text
