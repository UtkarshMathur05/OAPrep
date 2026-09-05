"""Connection helper. TODO(backend): implement (psycopg.connect(DATABASE_URL))."""

from contextlib import contextmanager

from app.config import DATABASE_URL


@contextmanager
def get_conn():
    raise NotImplementedError
