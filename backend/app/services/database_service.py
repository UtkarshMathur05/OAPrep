"""PostgreSQL access. TODO(backend): implement with psycopg + pgvector."""

from app.config import DATABASE_URL


def get_connection():
    raise NotImplementedError


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
