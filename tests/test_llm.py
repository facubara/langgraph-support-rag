from __future__ import annotations

import time

import pytest

from app.llm.base import LLMClient, LLMResponse
from app.llm.factory import ResilientLLM


class FlakyLLM(LLMClient):
    """Fails `fail_times` then succeeds; optionally sleeps to trigger timeouts."""

    def __init__(self, model="flaky", fail_times=0, sleep=0.0):
        self.model = model
        self.fail_times = fail_times
        self.sleep = sleep
        self.calls = 0

    def complete(self, system: str, prompt: str) -> LLMResponse:
        self.calls += 1
        if self.sleep:
            time.sleep(self.sleep)
        if self.calls <= self.fail_times:
            raise RuntimeError("boom")
        return LLMResponse(text=f"ok from {self.model}", model=self.model)


def test_retries_then_succeeds():
    primary = FlakyLLM(fail_times=1)
    llm = ResilientLLM(primary, fallback=None, max_retries=2, timeout=5)
    resp = llm.complete("sys", "hi")
    assert resp.text == "ok from flaky"
    assert primary.calls == 2  # failed once, succeeded on retry


def test_falls_back_when_primary_exhausted():
    primary = FlakyLLM(model="primary", fail_times=99)
    fallback = FlakyLLM(model="fallback", fail_times=0)
    llm = ResilientLLM(primary, fallback=fallback, max_retries=2, timeout=5)
    resp = llm.complete("sys", "hi")
    assert resp.text == "ok from fallback"
    assert primary.calls == 3  # initial + 2 retries


def test_timeout_triggers_fallback():
    slow = FlakyLLM(model="slow", sleep=0.5)
    fast = FlakyLLM(model="fast")
    llm = ResilientLLM(slow, fallback=fast, max_retries=1, timeout=0.05)
    resp = llm.complete("sys", "hi")
    assert resp.text == "ok from fast"


def test_raises_when_no_fallback_and_all_fail():
    primary = FlakyLLM(fail_times=99)
    llm = ResilientLLM(primary, fallback=None, max_retries=1, timeout=5)
    with pytest.raises(RuntimeError):
        llm.complete("sys", "hi")
