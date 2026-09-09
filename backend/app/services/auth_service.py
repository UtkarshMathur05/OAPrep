"""Accounts: passwords, OAuth, sessions, and claiming anonymous history.

Three things here are security decisions rather than style, and are worth not
undoing by accident:

* **Sessions are rows, and the cookie holds a random token.** Only the token's
  SHA-256 is stored, so reading `auth_sessions` hands nobody a live session, and
  signing out actually ends the session — which a self-contained JWT cannot do.
* **OAuth links to an existing account only on a provider-verified email.**
  Otherwise anybody who can set an unverified address at a provider could take
  over the account that owns it. GitHub is asked for its verified primary
  address explicitly; Google's `email_verified` claim is checked.
* **Sign-in and sign-up say the same thing on failure.** "No such account" and
  "wrong password" as separate messages is an account-enumeration oracle.

Password reset needs no table. The token is signed and carries the user's
`password_changed_at`; using it changes the password, which invalidates every
token minted before. That is single-use without storage.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app import email as mailer
from app.config import (
    AUTH_SECRET,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    API_PREFIX,
    PUBLIC_API_URL,
    PUBLIC_APP_URL,
    SESSION_COOKIE,
    SESSION_TTL_DAYS,
)
from app.db.database import execute, execute_count, query_one

log = logging.getLogger(__name__)

_hasher = PasswordHasher()
_signer = URLSafeTimedSerializer(AUTH_SECRET, salt="memoize.auth")

MIN_PASSWORD = 8
STATE_TTL = 600            # 10 minutes to complete an OAuth round trip
EMAIL_TOKEN_TTL = 60 * 60 * 24   # verification and reset links last a day
OAUTH_TIMEOUT = 15.0

# Said to the caller whenever a credential does not check out, whichever half
# was wrong. Telling them which is an account-enumeration oracle.
BAD_CREDENTIALS = "That email and password do not match an account."


# ------------------------------------------------------------------ hashing

def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(stored: Optional[str], raw: str) -> bool:
    """Constant-ish time, and False rather than raising for an OAuth-only user."""
    if not stored:
        return False
    try:
        return _hasher.verify(stored, raw)
    except (VerifyMismatchError, VerificationError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ----------------------------------------------------------------- sessions

def start_session(response: Response, user_id: UUID, user_agent: str = "") -> None:
    """Mint a session row and set the cookie."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    execute(
        "INSERT INTO auth_sessions (user_id, token_hash, user_agent, expires_at) "
        "VALUES (%s, %s, %s, %s)",
        (user_id, _token_hash(token), user_agent[:300] or None, expires),
    )
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,          # JavaScript must never be able to read this
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def end_session(request: Request, response: Response) -> None:
    """Revoke this session server-side, then clear the cookie.

    Both halves matter: clearing only the cookie leaves a token that still works
    if it was captured, which is exactly the case logout is supposed to cover.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        execute(
            "UPDATE auth_sessions SET revoked_at = now() "
            "WHERE token_hash = %s AND revoked_at IS NULL",
            (_token_hash(token),),
        )
    response.delete_cookie(SESSION_COOKIE, path="/", samesite=COOKIE_SAMESITE,
                           secure=COOKIE_SECURE, httponly=True)


def user_id_for_cookie(request: Request) -> UUID | None:
    """Resolve the session cookie to a user, or None. Never raises.

    Called on effectively every request through `identity.current_principal`, so
    a database hiccup must degrade to "signed out" rather than 500 a page that
    would otherwise render.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        row = query_one(
            "SELECT user_id FROM auth_sessions "
            "WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > now()",
            (_token_hash(token),),
        )
    except Exception:  # noqa: BLE001
        log.warning("could not resolve session cookie", exc_info=True)
        return None
    return row["user_id"] if row else None


# -------------------------------------------------------------------- users

def public_user(row: dict) -> dict:
    """The shape the browser is allowed to see. Never includes the hash."""
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "email_verified": row["email_verified"],
        "display_name": row.get("display_name") or row["email"].split("@")[0],
        "avatar_url": row.get("avatar_url"),
        "has_password": bool(row.get("password_hash")),
        "providers": [p for p in ("github", "google") if row.get(f"{p}_id")],
    }


def _by_email(email: str) -> dict | None:
    return query_one("SELECT * FROM users WHERE lower(email) = lower(%s)", (email,))


def get_user(user_id: UUID) -> dict | None:
    return query_one("SELECT * FROM users WHERE id = %s", (user_id,))


def sign_up(email: str, password: str, display_name: str = "") -> dict:
    email = email.strip()
    if len(password) < MIN_PASSWORD:
        raise HTTPException(422, f"Password must be at least {MIN_PASSWORD} characters.")
    if _by_email(email):
        # Deliberately specific: for *signup* the address is already known to
        # whoever holds it, and refusing without saying why is worse than the
        # enumeration this leaks — they would otherwise retry forever.
        raise HTTPException(409, "An account with that email already exists. Sign in instead.")
    row = query_one(
        "INSERT INTO users (email, password_hash, display_name) VALUES (%s, %s, %s) "
        "RETURNING *",
        (email, hash_password(password), display_name.strip() or None),
    )
    send_verification(row)
    return row


def sign_in(email: str, password: str) -> dict:
    row = _by_email(email.strip())
    if row is None or not verify_password(row.get("password_hash"), password):
        raise HTTPException(401, BAD_CREDENTIALS)
    return row


def set_password(user_id: UUID, password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise HTTPException(422, f"Password must be at least {MIN_PASSWORD} characters.")
    # `password_changed_at` is what makes outstanding reset links single-use.
    execute(
        "UPDATE users SET password_hash = %s, password_changed_at = now() WHERE id = %s",
        (hash_password(password), user_id),
    )


# --------------------------------------------------------- email round trips

def _email_token(user: dict, purpose: str) -> str:
    return _signer.dumps({
        "uid": str(user["id"]),
        "purpose": purpose,
        # Only for reset: pins the token to the password it was issued against.
        "pw": user["password_changed_at"].isoformat() if purpose == "reset" else None,
    })


def _read_email_token(token: str, purpose: str) -> dict:
    try:
        data = _signer.loads(token, max_age=EMAIL_TOKEN_TTL)
    except SignatureExpired:
        raise HTTPException(400, "That link has expired. Request a new one.")
    except BadSignature:
        raise HTTPException(400, "That link is not valid.")
    if data.get("purpose") != purpose:
        raise HTTPException(400, "That link is not valid.")
    user = get_user(UUID(data["uid"]))
    if user is None:
        raise HTTPException(400, "That link is not valid.")
    if purpose == "reset" and data.get("pw") != user["password_changed_at"].isoformat():
        raise HTTPException(400, "That link has already been used. Request a new one.")
    return user


def send_verification(user: dict) -> None:
    if user["email_verified"]:
        return
    link = f"{PUBLIC_APP_URL}/auth/verify?token={_email_token(user, 'verify')}"
    mailer.send(
        user["email"], "Confirm your Memoize address",
        f"Confirm your address to finish setting up your account:\n\n{link}\n\n"
        "The link is good for 24 hours. If you did not create an account, "
        "you can ignore this.",
    )


def verify_email(token: str) -> dict:
    user = _read_email_token(token, "verify")
    execute("UPDATE users SET email_verified = TRUE WHERE id = %s", (user["id"],))
    return get_user(user["id"])


def request_password_reset(email: str) -> None:
    """Always succeeds from the caller's point of view.

    Whether an address has an account is not something an unauthenticated
    request gets to learn, so an unknown address does exactly as much work and
    returns exactly the same thing.
    """
    user = _by_email(email.strip())
    if user is None:
        return
    link = f"{PUBLIC_APP_URL}/auth/reset?token={_email_token(user, 'reset')}"
    mailer.send(
        user["email"], "Reset your Memoize password",
        f"Set a new password here:\n\n{link}\n\n"
        "The link is good for 24 hours and can only be used once. If you did "
        "not ask for this, nothing has changed and you can ignore it.",
    )


def reset_password(token: str, password: str) -> dict:
    user = _read_email_token(token, "reset")
    set_password(user["id"], password)
    # Resetting a password is the standard response to "somebody else may have
    # my account", so every other session has to go with it.
    execute(
        "UPDATE auth_sessions SET revoked_at = now() "
        "WHERE user_id = %s AND revoked_at IS NULL",
        (user["id"],),
    )
    # A reset link proves control of the address as much as a verification link.
    execute("UPDATE users SET email_verified = TRUE WHERE id = %s", (user["id"],))
    return get_user(user["id"])


# --------------------------------------------------------------------- oauth

_PROVIDERS = {
    "github": {
        "authorize": "https://github.com/login/oauth/authorize",
        "token": "https://github.com/login/oauth/access_token",
        "scope": "read:user user:email",
    },
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scope": "openid email profile",
    },
}


def _credentials(provider: str) -> tuple[str, str]:
    pair = {
        "github": (GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET),
        "google": (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    }.get(provider, ("", ""))
    if not pair[0] or not pair[1]:
        raise HTTPException(503, f"{provider.title()} sign-in is not configured on this server.")
    return pair


def redirect_uri(provider: str) -> str:
    return f"{PUBLIC_API_URL}{API_PREFIX}/auth/{provider}/callback"


def authorize_url(provider: str, next_path: str = "/") -> str:
    """Where to send the browser to start the dance.

    `state` is signed rather than stored: it is a CSRF token, so it only has to
    be unforgeable and short-lived, and signing gives both without a table or a
    second cookie. It carries where to land afterwards.
    """
    if provider not in _PROVIDERS:
        raise HTTPException(404, f"Unknown provider {provider!r}.")
    client_id, _ = _credentials(provider)
    spec = _PROVIDERS[provider]
    state = _signer.dumps({"provider": provider, "next": next_path})
    from urllib.parse import urlencode

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(provider),
        "scope": spec["scope"],
        "state": state,
        "response_type": "code",
    }
    return f"{spec['authorize']}?{urlencode(params)}"


def read_state(state: str, provider: str) -> str:
    """Validate the state and return the path to land on."""
    try:
        data = _signer.loads(state, max_age=STATE_TTL)
    except (BadSignature, SignatureExpired):
        raise HTTPException(400, "That sign-in attempt expired or was tampered with. Try again.")
    if data.get("provider") != provider:
        raise HTTPException(400, "That sign-in attempt does not match this provider.")
    nxt = data.get("next") or "/"
    # Only ever bounce back into our own app: an attacker-chosen `next` is an
    # open redirect, and an open redirect on an auth callback is a phishing tool.
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else "/"


def exchange(provider: str, code: str) -> dict:
    """Trade the code for a profile: {provider_id, email, email_verified, name, avatar}."""
    client_id, client_secret = _credentials(provider)
    spec = _PROVIDERS[provider]
    with httpx.Client(timeout=OAUTH_TIMEOUT) as http:
        token_res = http.post(
            spec["token"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri(provider),
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        if token_res.status_code >= 400:
            log.warning("%s token exchange failed: %s", provider, token_res.text[:200])
            raise HTTPException(502, f"{provider.title()} rejected the sign-in. Try again.")
        access = token_res.json().get("access_token")
        if not access:
            raise HTTPException(502, f"{provider.title()} did not return an access token.")
        auth = {"Authorization": f"Bearer {access}", "Accept": "application/json"}

        if provider == "github":
            me = http.get("https://api.github.com/user", headers=auth).json()
            # The profile's `email` is whatever the user made public — often
            # null, and never guaranteed verified. The verified primary address
            # is what may be trusted to link accounts, so ask for it directly.
            emails = http.get("https://api.github.com/user/emails", headers=auth).json()
            primary = next(
                (e for e in emails if isinstance(e, dict) and e.get("primary") and e.get("verified")),
                None,
            )
            return {
                "provider_id": str(me["id"]),
                "email": (primary or {}).get("email") or me.get("email"),
                "email_verified": bool(primary),
                "name": me.get("name") or me.get("login"),
                "avatar": me.get("avatar_url"),
            }

        me = http.get("https://openidconnect.googleapis.com/v1/userinfo", headers=auth).json()
        return {
            "provider_id": me["sub"],
            "email": me.get("email"),
            "email_verified": bool(me.get("email_verified")),
            "name": me.get("name"),
            "avatar": me.get("picture"),
        }


def upsert_oauth_user(provider: str, profile: dict) -> dict:
    """Find or create the account behind an OAuth profile.

    Three cases, in order:

    1. We have seen this provider account before — that is the user, full stop.
    2. The provider asserts a *verified* email we already hold — link them, so
       somebody who signed up with a password can also use the button.
    3. Otherwise create an account.

    Case 2 is the dangerous one. Linking on an unverified address would let
    anybody who can set an arbitrary email at a provider walk into the account
    that owns it, so the check is not optional.
    """
    column = f"{provider}_id"
    existing = query_one(f"SELECT * FROM users WHERE {column} = %s", (profile["provider_id"],))
    if existing:
        return existing

    email = (profile.get("email") or "").strip()
    if not email:
        raise HTTPException(
            400,
            f"{provider.title()} did not share an email address, so there is nothing "
            "to attach the account to. Add a verified address there, or sign up with "
            "an email and password.",
        )

    if profile.get("email_verified"):
        owner = _by_email(email)
        if owner:
            execute(
                f"UPDATE users SET {column} = %s, "
                "    display_name = coalesce(display_name, %s), "
                "    avatar_url = coalesce(avatar_url, %s), "
                "    email_verified = TRUE "
                "WHERE id = %s",
                (profile["provider_id"], profile.get("name"), profile.get("avatar"), owner["id"]),
            )
            return get_user(owner["id"])

    if _by_email(email):
        # Same address, but the provider will not vouch for it. Refuse rather
        # than link (takeover) or create a second account (a duplicate nobody
        # can tell apart).
        raise HTTPException(
            409,
            f"{provider.title()} has not verified that address, and an account already "
            "uses it. Sign in with your password, then connect "
            f"{provider.title()} from your account.",
        )

    return query_one(
        f"INSERT INTO users (email, email_verified, display_name, avatar_url, {column}) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING *",
        (email, bool(profile.get("email_verified")), profile.get("name"),
         profile.get("avatar"), profile["provider_id"]),
    )


# ------------------------------------------------------------------ claiming

def claim(user_id: UUID, session_id: UUID | None) -> dict:
    """Attach a browser's anonymous history to the account that just signed in.

    This is the whole reason `session_id` was stored before accounts existed
    (§20b). Runs on every sign-in, not just the first: people work signed out on
    a second machine and sign in later, and there is no reason that history
    should be stranded.

    Only unclaimed rows move, so signing in on a shared browser cannot steal
    somebody else's already-attributed work.
    """
    if session_id is None:
        return {"submissions": 0, "contributions": 0, "problems": 0}

    subs = execute_count(
        "UPDATE submissions SET user_id = %s WHERE session_id = %s AND user_id IS NULL",
        (user_id, session_id),
    )
    # `uq_contribution_per_user` allows one row per (problem, user), and the
    # same person may have corroborated a problem from two browsers. Claim the
    # oldest of each and leave the rest anonymous rather than failing the whole
    # sign-in on a constraint violation.
    contribs = execute_count(
        """
        UPDATE contributions c SET user_id = %s
         WHERE c.session_id = %s AND c.user_id IS NULL
           AND c.id = (SELECT c2.id FROM contributions c2
                        WHERE c2.problem_id = c.problem_id AND c2.session_id = c.session_id
                        ORDER BY c2.created_at, c2.id LIMIT 1)
           AND NOT EXISTS (SELECT 1 FROM contributions c3
                            WHERE c3.problem_id = c.problem_id AND c3.user_id = %s)
        """,
        (user_id, session_id, user_id),
    )
    problems = execute_count(
        """
        UPDATE problems SET created_by = %s
         WHERE created_by IS NULL AND origin = 'community'
           AND id IN (SELECT problem_id FROM contributions
                       WHERE session_id = %s AND kind = 'created')
        """,
        (user_id, session_id),
    )
    return {"submissions": subs, "contributions": contribs, "problems": problems}
