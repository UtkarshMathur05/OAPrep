"""PostgreSQL connection helper.

One connection per unit of work, opened and closed by `get_conn()`. No pool:
at demo scale a local connect costs ~5ms, and psycopg_pool is one more moving
part to debug at hour 30. Swap in `psycopg_pool.ConnectionPool` if that ever
shows up in a profile.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import DATABASE_URL


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    """Yield a connection, committing on success and rolling back on error.

    Rows come back as dicts (`row["title"]`, not `row[2]`) so the service layer
    never depends on SELECT column order.
    """
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        _register_vector(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _register_vector(conn: psycopg.Connection) -> None:
    """Teach psycopg the `vector` type, so embeddings adapt to/from lists."""
    from pgvector.psycopg import register_vector

    try:
        register_vector(conn)
    except psycopg.ProgrammingError as exc:
        raise RuntimeError(
            "pgvector is not installed in this database. Start it with "
            "`docker compose up -d`, or run: CREATE EXTENSION vector;"
        ) from exc


def query(sql: str, params: Any = None) -> list[dict]:
    """Run a SELECT and return all rows."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def query_one(sql: str, params: Any = None) -> dict | None:
    """Run a SELECT and return the first row, or None."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql: str, params: Any = None) -> dict | None:
    """Run an INSERT/UPDATE/DELETE. Returns the RETURNING row when there is one."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description is None:
            return None
        return cur.fetchone()


def healthcheck() -> dict:
    """Cheap liveness probe used by GET /health/db."""
    row = query_one(
        "SELECT current_database() AS db, "
        "       (SELECT count(*) FROM problems) AS problems, "
        "       (SELECT count(*) FROM problems WHERE embedding IS NOT NULL) AS embedded"
    )
    return dict(row or {})
