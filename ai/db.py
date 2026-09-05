"""Postgres access for the AI package.

`ai/` must not import `backend.*` (CLAUDE.md §24 boundaries), and retrieval needs
pgvector, so the AI side owns this ~30-line helper rather than sharing the
backend's. Raw psycopg, no ORM.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://recollect:recollect@localhost:5432/recollect"
)


CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))


class DBError(RuntimeError):
    """Database unreachable or misconfigured; callers degrade rather than 500."""


@lru_cache(maxsize=1)
def connect():
    """Process-wide connection with the pgvector adapter registered.

    Cached because retrieval runs per request and reconnecting each time is pure
    latency. Call reset() if the connection goes stale.
    """
    import psycopg
    from pgvector.psycopg import register_vector

    try:
        # connect_timeout matters: without it a down Postgres hangs the request
        # instead of degrading (CLAUDE.md §20).
        conn = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=CONNECT_TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        raise DBError(f"cannot connect to Postgres at {DATABASE_URL!r}: {exc}") from exc

    register_vector(conn)
    return conn


def reset() -> None:
    """Drop the cached connection (after a restart, or a stale-socket error)."""
    try:
        connect.cache_info()
        conn = connect()
        conn.close()
    except Exception:  # noqa: BLE001
        pass
    finally:
        connect.cache_clear()


def query(sql: str, params: tuple = ()) -> list[tuple]:
    """Run a read query and return all rows."""
    with connect().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()
