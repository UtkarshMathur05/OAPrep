"""Global exception handling.

§20: every external dependency can fail, and the user must see a useful message
rather than a stack trace. Nothing should ever escape as a bare 500.
"""

from __future__ import annotations

import logging

import httpx
import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("memoize")


def _json(status: int, detail: str, hint: str | None = None) -> JSONResponse:
    body = {"detail": detail}
    if hint:
        body["hint"] = hint
    return JSONResponse(status_code=status, content=body)


def register(app: FastAPI) -> None:
    """Attach handlers, most specific first."""

    @app.exception_handler(psycopg.OperationalError)
    def _db_down(request: Request, exc: psycopg.OperationalError):
        log.error("database unreachable on %s: %s", request.url.path, exc)
        return _json(503, "Database unavailable.",
                     "Is Postgres running? `docker compose up -d`")

    @app.exception_handler(psycopg.Error)
    def _db_error(request: Request, exc: psycopg.Error):
        # Includes UndefinedColumn — the usual sign of a stale pgdata volume.
        log.exception("database error on %s", request.url.path)
        return _json(500, f"Database error: {type(exc).__name__}",
                     "If a column is missing, your volume predates a schema "
                     "change — see database/README.md")

    @app.exception_handler(httpx.HTTPError)
    def _upstream(request: Request, exc: httpx.HTTPError):
        log.error("upstream failure on %s: %s", request.url.path, exc)
        return _json(502, f"Upstream service failed: {type(exc).__name__}",
                     "Judge0 or Gemini did not respond. Set USE_MOCK_AI=true "
                     "to keep the flow working.")

    @app.exception_handler(NotImplementedError)
    def _not_built(request: Request, exc: NotImplementedError):
        # Hit when USE_MOCK_AI=false but the ai/ module is still a stub.
        log.warning("unimplemented path %s", request.url.path)
        return _json(501, "That part of the pipeline is not implemented yet.",
                     "Set USE_MOCK_AI=true in .env to use canned responses.")

    @app.exception_handler(Exception)
    def _unhandled(request: Request, exc: Exception):
        # Last resort. Log the traceback; return a message, never internals.
        log.exception("unhandled error on %s", request.url.path)
        return _json(500, "Something went wrong. Check the backend logs.")
