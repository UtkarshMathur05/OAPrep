"""Disk cache for AI responses, keyed by a hash of the input.

Why this exists: a live demo should not depend on Gemini being fast, up, or on
the venue wifi working. Every call goes through here, so the second run of the
golden demo path is instant, deterministic and offline.

Set RECOLLECT_NO_CACHE=1 while tuning prompts, or the cache will happily serve
you yesterday's answer.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Optional

# `or` not a getenv default: an env var set to empty (RECOLLECT_CACHE_DIR= in
# .env) returns "", and Path("") is the current directory, which scatters
# cache files wherever the process happens to be running.
CACHE_DIR = Path(os.getenv("RECOLLECT_CACHE_DIR") or Path(__file__).parent / ".cache")


def enabled() -> bool:
    return os.getenv("RECOLLECT_NO_CACHE", "").strip() not in ("1", "true", "yes")


def key(*parts: Any) -> str:
    """Stable hash over the call's inputs. Order matters; keep it consistent."""
    blob = "\x00".join(
        json.dumps(p, sort_keys=True, default=str) if not isinstance(p, str) else p
        for p in parts
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _path(k: str) -> Path:
    return CACHE_DIR / f"{k}.json"


def get(k: str) -> Optional[Any]:
    if not enabled():
        return None
    path = _path(k)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # A corrupt entry is not worth crashing over; treat it as a miss.
        return None


def put(k: str, value: Any) -> None:
    if not enabled():
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Write-then-rename so an interrupted run never leaves half a JSON file.
        tmp = _path(k).with_suffix(".tmp")
        tmp.write_text(json.dumps(value), encoding="utf-8")
        tmp.replace(_path(k))
    except OSError:
        pass


def call(k: str, fn: Callable[[], Any]) -> Any:
    """Return the cached value for `k`, else run `fn()` and cache it."""
    hit = get(k)
    if hit is not None:
        return hit
    value = fn()
    put(k, value)
    return value
