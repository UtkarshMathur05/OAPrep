"""Settings loaded from the repo-root .env. TODO(backend): extend as needed."""

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://recollect:recollect@localhost:5432/recollect")
def _real(value: str) -> str:
    """Treat .env.example placeholders as unset, so readiness checks are honest."""
    v = (value or "").strip()
    return "" if not v or v.startswith("your_") or v.endswith("_here") else v


GEMINI_API_KEY = _real(os.getenv("GEMINI_API_KEY", ""))
JUDGE0_URL = os.getenv("JUDGE0_URL", "https://ce.judge0.com")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY", "")
JUDGE0_API_HOST = os.getenv("JUDGE0_API_HOST", "")
USE_MOCK_AI = os.getenv("USE_MOCK_AI", "true").lower() == "true"
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if o.strip()]


# --------------------------------------------------------------------- auth
#
# Everything here has a working default for local development, so `git clone`
# + `docker compose up` still gets you a signed-in session without registering
# an OAuth app or an email provider. Nothing here has a *safe* default for
# production, which is what `auth_warnings()` is for.

# Signs the session cookie, the OAuth state, and the email links. Rotating it
# signs everybody out and invalidates outstanding verification links, which is
# the correct behaviour if it ever leaks.
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-only-insecure-secret-change-me")
AUTH_SECRET_IS_DEFAULT = AUTH_SECRET == "dev-only-insecure-secret-change-me"

SESSION_COOKIE = os.getenv("SESSION_COOKIE", "memoize_session")
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))

# Where the browser is, and where this API is. Both are needed literally: OAuth
# redirect URIs must match what is registered with the provider byte for byte,
# and email links have to point at the app rather than the API.
#
# When one process serves both, they are the same URL — and on Render that URL
# is injected as RENDER_EXTERNAL_URL, so the single-origin deployment needs no
# manual value at all. Getting these wrong is not a visible failure: it is an
# email link that 404s, or a cookie that is silently never sent.
_EXTERNAL_URL = (os.getenv("RENDER_EXTERNAL_URL", "") or "").rstrip("/")
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", _EXTERNAL_URL or "http://localhost:5173").rstrip("/")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", _EXTERNAL_URL or "http://localhost:8000").rstrip("/")

# Secure cookies require HTTPS, so a hardcoded True would break local dev and a
# hardcoded False would ship a session cookie in the clear. Derive it, and let
# it be overridden for the odd deployment that terminates TLS elsewhere.
COOKIE_SECURE = os.getenv(
    "COOKIE_SECURE", "true" if PUBLIC_APP_URL.startswith("https://") else "false"
).lower() == "true"
# Lax is right while the app and API share a registrable domain (localhost:5173
# and localhost:8000 do — ports do not affect same-site). Split them across
# domains and this has to become "none", which also forces COOKIE_SECURE.
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()

GITHUB_CLIENT_ID = _real(os.getenv("GITHUB_CLIENT_ID", ""))
GITHUB_CLIENT_SECRET = _real(os.getenv("GITHUB_CLIENT_SECRET", ""))
GOOGLE_CLIENT_ID = _real(os.getenv("GOOGLE_CLIENT_ID", ""))
GOOGLE_CLIENT_SECRET = _real(os.getenv("GOOGLE_CLIENT_SECRET", ""))

# console | resend | smtp. "console" prints the link to the server log, so the
# whole verify/reset flow is testable with no provider account and no network —
# the same degradation idea as USE_MOCK_AI.
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "console").lower()
EMAIL_FROM = os.getenv("EMAIL_FROM", "Memoize <onboarding@resend.dev>")
RESEND_API_KEY = _real(os.getenv("RESEND_API_KEY", ""))
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# How many distinct problems a signed-out visitor may run before being asked to
# sign in. A nudge, not a wall: clearing site data mints a new session id and
# resets it, and pretending otherwise would be the same mistake as treating a
# session id as a credential.
GUEST_PROBLEM_LIMIT = int(os.getenv("GUEST_PROBLEM_LIMIT", "2"))


# --------------------------------------------------------------- deployment
#
# The built frontend, when this process is also serving it. Empty in local
# development, where Vite serves the app on its own port.
#
# Serving both from one origin is not a packaging convenience — it is what
# keeps the session cookie working. `onrender.com` is on the Public Suffix
# List, so `app.onrender.com` and `api.onrender.com` are different *sites*, and
# a SameSite=Lax cookie is not sent between them. One origin means Lax is
# correct, CORS is unnecessary, and nothing depends on third-party cookies
# (which Safari blocks outright).
_DEFAULT_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "dist",
)
# `or` rather than a getenv default: .env.example ships the key empty, and an
# empty string would otherwise win over the default and disable serving.
FRONTEND_DIST = os.getenv("FRONTEND_DIST") or _DEFAULT_DIST

# Every API route lives under this prefix, in development as well as in
# production. It is not decoration: served from one origin, `/problems` is both
# an API route and a page a person can navigate to, and one of them has to
# lose. Keeping the prefix on locally too means the deployed layout is the one
# that gets exercised.
API_PREFIX = "/api"
SERVE_FRONTEND = os.path.isdir(FRONTEND_DIST)


def auth_warnings() -> list[str]:
    """Configuration that is fine locally and wrong in production."""
    out = []
    if AUTH_SECRET_IS_DEFAULT:
        out.append("AUTH_SECRET is the built-in development value — set a real one.")
    if PUBLIC_APP_URL.startswith("https://") and not COOKIE_SECURE:
        out.append("PUBLIC_APP_URL is https but COOKIE_SECURE is false.")
    if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
        out.append("COOKIE_SAMESITE=none requires COOKIE_SECURE=true; browsers drop the cookie otherwise.")
    if not (GITHUB_CLIENT_ID or GOOGLE_CLIENT_ID):
        out.append("No OAuth provider configured — only email and password will work.")
    if EMAIL_PROVIDER == "console":
        out.append("EMAIL_PROVIDER=console — verification and reset links are printed to the log, not sent.")
    if _registrable(PUBLIC_APP_URL) != _registrable(PUBLIC_API_URL) and COOKIE_SAMESITE != "none":
        out.append(
            f"PUBLIC_APP_URL and PUBLIC_API_URL are different sites and COOKIE_SAMESITE={COOKIE_SAMESITE} "
            "— the session cookie will not be sent, so sign-in will appear to work and then not. "
            "Serve both from one origin, or set COOKIE_SAMESITE=none."
        )
    return out


def _registrable(url: str) -> str:
    """The *site* a URL belongs to, well enough to catch the mistake above.

    Not a Public Suffix List lookup, and it does not need to be — this only has
    to notice when two of our own URLs are cross-site. Ordinarily that is the
    last two labels, so `app.example.com` and `api.example.com` are one site and
    do not warn. The exception is the multi-label public suffixes the free
    hosting tiers hand out: `onrender.com` is itself on the PSL, which makes
    `app.onrender.com` and `api.onrender.com` two different sites, and a
    SameSite=Lax cookie is not sent between them.
    """
    multi_label_suffixes = (
        ".onrender.com", ".vercel.app", ".netlify.app", ".github.io",
        ".herokuapp.com", ".fly.dev", ".pages.dev", ".up.railway.app",
    )
    host = url.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()
    for suffix in multi_label_suffixes:
        if host.endswith(suffix):
            return host  # every subdomain is its own site
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) > 2 else host
