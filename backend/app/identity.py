"""Who is making this request.

Two things identify a caller, and they are not the same kind of thing:

* **session** — an opaque UUID the browser generates once and stores, sent as
  `X-Session-Id`. Identifies a *browser*, not a person. Free to mint: clearing
  site data produces a new one. Never a credential.
* **user** — a real account, established by the signed session cookie and
  backed by a row in `users`. This is the one you may trust.

**This module is the seam.** Nothing else reads the header or the cookie.

§20b planned for this by having `current_session()` start returning a user id,
so that "no other file changes". That turned out to be the wrong shape: one
column holding two id spaces cannot be foreign-keyed, cannot distinguish an
anonymous row from a user's, and makes claiming a destructive rewrite. So both
travel together and the storage keeps both columns — see `11_auth.sql`.

Callers should ask for what they actually need. `principal.user_id` for
anything that must be a person; `principal.session_id` for anonymous
attribution that will be claimed later.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Request

HEADER = "X-Session-Id"


@dataclass(frozen=True)
class Principal:
    """The caller. Either half may be absent, including both."""

    user_id: UUID | None = None
    session_id: UUID | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    @property
    def owner(self) -> UUID | None:
        """Whichever id owns this request's activity, preferring the account.

        For "what has this caller done", a signed-in user's history is theirs
        across browsers, so the account wins whenever there is one.
        """
        return self.user_id or self.session_id


def current_session(request: Request) -> UUID | None:
    """The anonymous browser session, or None when absent or malformed.

    Never raises. An unidentified caller is a normal, supported state — they can
    still browse and run code — so a bad header degrades to anonymous rather
    than 400ing a request that would otherwise work.
    """
    raw = request.headers.get(HEADER)
    if not raw:
        return None
    try:
        return UUID(raw)
    except (ValueError, AttributeError, TypeError):
        return None


def current_principal(request: Request) -> Principal:
    """The caller's account (if signed in) and browser session (if sent).

    Imported lazily because `auth_service` reads the database, and importing it
    at module scope would make this seam — which every request touches — depend
    on the database being reachable just to answer "nobody is signed in".
    """
    from app.services import auth_service

    return Principal(
        user_id=auth_service.user_id_for_cookie(request),
        session_id=current_session(request),
    )
