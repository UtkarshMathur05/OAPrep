"""Step 3 — Embedding generation for problems and genome queries.

A thin wrap of gemini_client so callers do not reach past this package for
retrieval concerns. Caching, batching, dimension checks and quota-aware retry
all live in gemini_client.
"""

from __future__ import annotations

from typing import List

from ai import gemini_client


def embed_text(text: str) -> List[float]:
    """Embed one string. Returns EMBEDDING_DIM floats."""
    return gemini_client.embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed many strings, reusing anything already cached."""
    return gemini_client.embed_batch(texts)
