"""PostgreSQL access.

Connections come from app.db.database — do not open your own here.
TODO(backend): implement the queries (tasks B3, B5, B6).
"""

from app.db.database import execute, query, query_one  # noqa: F401


def list_problems(limit: int = 20):
    raise NotImplementedError


def get_problem(problem_id: str):
    raise NotImplementedError


def save_memory(genome, raw_transcript: str) -> str:
    raise NotImplementedError


def get_test_cases(problem_id: str):
    raise NotImplementedError


def save_submission(problem_id: str, code: str, language: str, result) -> str:
    raise NotImplementedError
