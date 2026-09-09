"""FastAPI entrypoint. Routes are thin; logic belongs in app/services."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import errors
from app.config import (
    API_PREFIX, CORS_ORIGINS, FRONTEND_DIST, GEMINI_API_KEY, SERVE_FRONTEND,
    USE_MOCK_AI, auth_warnings,
)
from app.api import auth, memory, search, reconstruct, verify, problems, contribute

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Fail at boot, not on the first request during a demo."""
    if not USE_MOCK_AI and not GEMINI_API_KEY:
        raise RuntimeError(
            "USE_MOCK_AI=false but GEMINI_API_KEY is unset. Add the key to .env, "
            "or set USE_MOCK_AI=true to run on canned responses."
        )
    # Warned, not raised: every one of these is correct for local development
    # and wrong in production, so refusing to boot would block the common case
    # to catch the rare one.
    for warning in auth_warnings():
        log.warning("auth config: %s", warning)
    yield


log = logging.getLogger(__name__)

app = FastAPI(title="Memoize API", version="0.1.0", lifespan=lifespan)

# Explicit origins, never "*" — credentials are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

errors.register(app)


# Under /api, always. `/problems` is a page as well as an endpoint once one
# origin serves both, and the collision has to be resolved somewhere — see
# API_PREFIX in config.py.
for _router in (auth, memory, search, reconstruct, verify, problems, contribute):
    app.include_router(_router.router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "mock_ai": USE_MOCK_AI, "ai_ready": bool(GEMINI_API_KEY)}


@app.get("/health/db")
def health_db():
    """Confirms the database is reachable and says how much corpus is loaded."""
    from app.db.database import healthcheck

    try:
        return {"status": "ok", **healthcheck()}
    except Exception as exc:  # noqa: BLE001 - a probe must report, not crash
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}")


# ------------------------------------------------------- the frontend, maybe
#
# Mounted last, so every API route above is matched first, and only when a
# build actually exists — locally there is none and Vite serves the app on its
# own port, unchanged.
#
# One origin for the app and the API is a cookie decision, not a packaging one:
# see FRONTEND_DIST in config.py.

if SERVE_FRONTEND:
    from fastapi.staticfiles import StaticFiles
    from starlette.exceptions import HTTPException as StarletteHTTPException

    def _wants_html(scope) -> bool:
        """A browser navigating, as opposed to a fetch that wanted JSON."""
        accept = dict(scope.get("headers") or {}).get(b"accept", b"").decode()
        return "text/html" in accept

    class _SPA(StaticFiles):
        """Static files, with client-side routes falling back to index.html.

        A deep link like /problems/two-sum is a real URL a person can paste, but
        there is no such file — React Router resolves it in the browser. The
        fallback is limited to requests that asked for HTML so that a mistyped
        API path still 404s as JSON instead of quietly returning a page.
        """

        async def get_response(self, path: str, scope):
            try:
                response = await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                # StaticFiles raises its 404 rather than returning one, so the
                # fallback has to be caught here as well as checked below.
                if exc.status_code == 404 and _wants_html(scope):
                    return await super().get_response("index.html", scope)
                raise
            if response.status_code == 404 and _wants_html(scope):
                return await super().get_response("index.html", scope)
            return response

    app.mount("/", _SPA(directory=FRONTEND_DIST, html=True), name="frontend")
    log.info("serving the frontend from %s", FRONTEND_DIST)
