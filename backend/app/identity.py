"""Who is making this request.

Right now: an anonymous session id the browser generates once and stores, sent
as `X-Session-Id`. There is no authentication, so this identifies a *browser*,
not a person, and the code says so rather than pretending otherwise.

**This module is the seam.** Every caller asks `current_session(request)` and
gets an opaque UUID; nothing else in the codebase reads the header or knows how
identity is established. When accounts land, this function starts returning the
authenticated user's id (falling back to the anonymous session for signed-out
traffic) and no other file changes.

What that buys, concretely: `submissions` and `contributions` already carry the
column, so today's activity stays attributable after the migration instead of
becoming an anonymous pile that has to be thrown away.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Request

HEADER = "X-Session-Id"


def current_session(request: Request) -> UUID | None:
    """The caller's session, or None when the header is absent or malformed.

    Never raises. An unidentified caller is a normal, supported state — they can
    still run code, they just accumulate no progress — so a bad header degrades
    to anonymous rather than 400ing a request that would otherwise work.
    """
    raw = request.headers.get(HEADER)
    if not raw:
        return None
    try:
        return UUID(raw)
    except (ValueError, AttributeError, TypeError):
        return None
