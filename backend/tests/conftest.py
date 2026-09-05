"""Shared fixtures.

These are integration tests: they hit the real Postgres from .env, because the
queries (pgvector, TEXT[], GIN filters) are most of what could break and a
mocked database would not exercise any of it.

Requires `docker compose up -d`. Nothing here calls Gemini or Judge0.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def any_slug(client: TestClient) -> str:
    """A slug that exists in whatever corpus is loaded."""
    rows = client.get("/problems", params={"limit": 1}).json()["problems"]
    if not rows:
        pytest.skip("no problems loaded — run the corpus pipeline")
    return rows[0]["slug"]
