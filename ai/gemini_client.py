"""Thin shared wrapper around the Gemini API.

Deliberately minimal: one text call, one embedding call, one JSON helper.
No agent framework, no retry orchestration.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
PROMPTS_DIR = Path(__file__).parent / "prompts"


@lru_cache(maxsize=1)
def get_client():
    """Lazily build the Gemini client so importing this module never fails."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set (copy .env.example to .env)")
    return genai.Client(api_key=api_key)


def load_prompt(name: str) -> str:
    """Read a prompt template from ai/prompts/<name>.txt."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def generate_text(prompt: str, *, model: str | None = None) -> str:
    response = get_client().models.generate_content(
        model=model or TEXT_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()


def generate_json(prompt: str, *, model: str | None = None) -> dict | list:
    """Ask for JSON and parse it, tolerating ```json fences."""
    raw = generate_text(prompt, model=model)
    return parse_json(raw)


def parse_json(raw: str) -> dict | list:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: grab the outermost {...} or [...] block.
        match = re.search(r"[\{\[].*[\}\]]", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def embed(text: str) -> List[float]:
    """Embed a single string. Returns EMBEDDING_DIM floats."""
    return embed_batch([text])[0]


def embed_batch(texts: List[str]) -> List[List[float]]:
    from google.genai import types

    response = get_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    return [list(e.values) for e in response.embeddings]
