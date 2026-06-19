from __future__ import annotations

import pytest

from app.config import settings
from app.rag.embeddings import cosine, embed
from app.rag.retriever import get_retriever


def test_embedding_is_deterministic_and_normalized():
    a = embed("duplicate charge refund")
    b = embed("duplicate charge refund")
    assert a == b
    assert cosine(a, a) == pytest.approx(1.0, abs=1e-6)


def test_retriever_finds_relevant_doc():
    top = get_retriever().search("I was charged twice for the same invoice", k=3)
    assert top[0]["title"] == "duplicate charges"
    assert top[0]["score"] > 0.3


@pytest.fixture()
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "rag.sqlite"))
    from app.store import run_store

    run_store.init_db()
    from app.graph import run_conversation

    return run_conversation, run_store


def test_faq_question_is_grounded_by_kb(run):
    run_conversation, run_store = run
    out = run_conversation("How do I cancel my subscription?")
    assert out["intent"] == "billing_question"
    assert out["status"] == "completed"
    assert "don't have enough information" not in out["response"]  # grounded, not refused

    detail = run_store.get_run(out["run_id"])
    billing_step = next(s for s in detail["steps"] if s["name"] == "billing_rag")
    assert len(billing_step["output"]["included"]) >= 1


def test_offtopic_question_excludes_context_and_refuses(run):
    run_conversation, _ = run
    out = run_conversation("Tell me a joke about platypuses")
    assert out["status"] == "completed"
    assert "don't have enough information" in out["response"]
