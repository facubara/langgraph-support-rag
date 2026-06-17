"""Loads the knowledge base, chunks it by paragraph, embeds each chunk, and serves
cosine top-k retrieval. `search` returns scored candidates; the caller applies a score
threshold to decide what is grounded enough to include."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .embeddings import cosine, embed

KB_DIR = Path(__file__).resolve().parent.parent / "kb"


def _split_paragraphs(raw: str) -> list[str]:
    chunks = []
    for block in raw.split("\n\n"):
        text = " ".join(line.strip() for line in block.splitlines() if line.strip())
        # Drop standalone markdown headings; keep substantive paragraphs.
        if text and not (text.startswith("#") and "\n" not in text and len(text) < 40):
            chunks.append(text.lstrip("# ").strip() if text.startswith("#") else text)
    return [c for c in chunks if c]


@dataclass
class Chunk:
    title: str
    text: str
    vector: list[float]


class Retriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks

    @classmethod
    def from_dir(cls, kb_dir: Path = KB_DIR) -> "Retriever":
        chunks: list[Chunk] = []
        for path in sorted(kb_dir.glob("*.md")):
            title = path.stem.replace("_", " ")
            for para in _split_paragraphs(path.read_text(encoding="utf-8")):
                chunks.append(Chunk(title=title, text=para, vector=embed(para)))
        return cls(chunks)

    def search(self, query: str, k: int = 5) -> list[dict]:
        q = embed(query)
        scored = sorted(
            ((cosine(q, c.vector), c) for c in self.chunks),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return [
            {"title": c.title, "text": c.text, "score": round(score, 4)}
            for score, c in scored[:k]
        ]


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever.from_dir()
