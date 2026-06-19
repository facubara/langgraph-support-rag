"""Retrieval-augmented generation: a small knowledge base, an embedding function, and a
cosine-similarity retriever. The default embedding is local and deterministic (no API key,
no heavy deps); a real embedding model or vector DB can replace it behind `Retriever`."""
