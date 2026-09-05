"""Step 3 — Embedding generation for problems and genome queries.

TODO(ai): wrap gemini_client.embed / embed_batch.
"""

from typing import List


def embed_text(text: str) -> List[float]:
    raise NotImplementedError


def embed_texts(texts: List[str]) -> List[List[float]]:
    raise NotImplementedError
