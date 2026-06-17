"""A local, deterministic embedding using the hashing trick.

Tokens are hashed into a fixed-dimension term-frequency vector, then L2-normalized so a dot
product is cosine similarity. This is intentionally simple: it demonstrates real vector
retrieval mechanics (embed → similarity → top-k) with zero external calls. Swap `embed` for
a model-backed embedding (OpenAI, Gemini, sentence-transformers) without touching the
retriever — the contract is just `str -> list[float]`.
"""

from __future__ import annotations

import hashlib
import math
import re

DIM = 256
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for tok in _tokens(text):
        idx = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % DIM
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
