"""Thin shared wrapper around the Gemini API.

Deliberately minimal: one text call, one structured call, one embedding call.
No agent framework, no retry orchestration beyond a bounded backoff.

Every call is disk-cached (see ai/cache.py), so re-running the demo path costs
nothing and works offline.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from ai import cache

load_dotenv()

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.1-flash-lite")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
# Free tier allows 100 embed requests/minute; a big corpus run needs patience.
EMBED_ATTEMPTS = int(os.getenv("EMBED_ATTEMPTS", "6"))
PROMPTS_DIR = Path(__file__).parent / "prompts"

T = TypeVar("T", bound=BaseModel)


class AIError(RuntimeError):
    """Any Gemini failure the caller should turn into a user-facing message.

    Callers catch this and degrade (CLAUDE.md §20) rather than 500.
    """


@lru_cache(maxsize=1)
def get_client():
    """Lazily build the Gemini client so importing this module never fails."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise AIError("GEMINI_API_KEY is not set (copy .env.example to .env)")
    return genai.Client(api_key=api_key)


def load_prompt(name: str) -> str:
    """Read a prompt template from ai/prompts/<name>.txt."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def _sleep_backoff(attempt: int) -> None:
    time.sleep(min(2 ** attempt, 8) + random.uniform(0, 0.5))


def _quota_sleep(attempt: int) -> float:
    """Per-minute quota needs a real wait, not an 8s backoff.

    The embedding free tier is 100 requests/minute and a batch of 32 counts as
    32, so the window has to actually roll over before retrying is worth it.
    """
    return min(20 * (attempt + 1), 70) + random.uniform(0, 3)


# 429 is rate limiting and 5xx is Gemini having a bad day; both are worth another
# go. A 400/403/404 will fail identically every time, so retrying just triples
# the wait before the user sees the error.
_RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}


def is_daily_quota(exc: Exception) -> bool:
    """True for 'you are out of requests until tomorrow', not 'slow down'.

    The free tier caps GenerateRequestsPerDayPerProjectPerModel at 20. Retrying
    that is pointless; callers should stop the whole run rather than grind
    through every remaining row three times.
    """
    text = str(exc)
    return "429" in text and ("PerDay" in text or "per day" in text.lower())


def _is_retryable(exc: Exception) -> bool:
    if is_daily_quota(exc):
        return False
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code in _RETRYABLE_CODES
    return True  # Unknown (network, timeout) - assume transient.


def generate_text(prompt: str, *, model: str | None = None) -> str:
    name = model or TEXT_MODEL
    key = cache.key("text", name, prompt)

    def run() -> str:
        response = get_client().models.generate_content(model=name, contents=prompt)
        return (response.text or "").strip()

    return cache.call(key, run)


def generate_structured(
    prompt: str,
    schema: Type[T],
    *,
    model: str | None = None,
    attempts: int = 3,
) -> T:
    """Ask Gemini for JSON matching `schema` and return a validated instance.

    Uses Gemini's native structured output (response_schema), not "return JSON"
    in the prompt plus regex repair — that removes the malformed-JSON failure
    mode entirely (CLAUDE.md §28).
    """
    from google.genai import types

    name = model or TEXT_MODEL
    key = cache.key("structured", name, prompt, schema.__name__)

    hit = cache.get(key)
    if hit is not None:
        try:
            return schema.model_validate(hit)
        except ValidationError:
            pass  # Schema changed since this was cached; re-fetch below.

    last: Exception | None = None
    for attempt in range(attempts):
        try:
            response = get_client().models.generate_content(
                model=name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            parsed = getattr(response, "parsed", None)
            if not isinstance(parsed, schema):
                # Older SDKs return text only; validate it ourselves.
                parsed = schema.model_validate_json(response.text or "")
            cache.put(key, parsed.model_dump(mode="json"))
            return parsed
        except Exception as exc:  # noqa: BLE001 - retry anything transient
            last = exc
            if not _is_retryable(exc):
                break
            if attempt < attempts - 1:
                _sleep_backoff(attempt)

    raise AIError(f"{schema.__name__} generation failed after {attempts} attempts: {last}") from last


def generate_json(prompt: str, *, model: str | None = None) -> dict | list:
    """Free-form JSON. Prefer generate_structured; this is the fallback path."""
    return parse_json(generate_text(prompt, model=model))


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
    """Embed many strings, reusing cached vectors for the ones already seen.

    Cached per-text rather than per-batch so a re-run with three new problems
    embeds three, not the whole corpus.
    """
    from google.genai import types

    if not texts:
        return []

    keys = [cache.key("embed", EMBEDDING_MODEL, EMBEDDING_DIM, t) for t in texts]
    out: List[List[float] | None] = [cache.get(k) for k in keys]
    missing = [i for i, vec in enumerate(out) if vec is None]

    if missing:
        response = None
        last: Exception | None = None
        for attempt in range(EMBED_ATTEMPTS):
            try:
                response = get_client().models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=[texts[i] for i in missing],
                    config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
                )
                break
            except Exception as exc:  # noqa: BLE001
                last = exc
                if not _is_retryable(exc) or attempt == EMBED_ATTEMPTS - 1:
                    raise AIError(f"embedding failed: {exc}") from exc
                delay = _quota_sleep(attempt) if "429" in str(exc) else 2 ** attempt
                print(f"    embedding rate-limited, waiting {delay:.0f}s "
                      f"(attempt {attempt + 1}/{EMBED_ATTEMPTS})")
                time.sleep(delay)
        if response is None:
            raise AIError(f"embedding failed: {last}")

        for i, embedding in zip(missing, response.embeddings):
            vec = list(embedding.values)
            if len(vec) != EMBEDDING_DIM:
                # A silent mismatch against VECTOR(768) is miserable to debug later.
                raise AIError(f"expected {EMBEDDING_DIM} dims, got {len(vec)}")
            out[i] = vec
            cache.put(keys[i], vec)

    return [vec for vec in out if vec is not None]
