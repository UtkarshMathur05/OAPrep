"""PostgreSQL access.

Connections come from app.db.database — do not open your own here.
Every query uses %s placeholders; never build SQL with f-strings.
"""

from typing import Any, Optional

from app.db.database import execute, query, query_one

# Columns shared by the list and detail views. `companies` is sliced to 5 for
# display — company_count carries the true total, so the UI can say
# "Google, Amazon and 124 others" without shipping 126 strings per row.
_SUMMARY_COLS = """
    id::text            AS id,
    slug,
    title,
    difficulty,
    platform,
    source_url,
    topics,
    companies[1:5]      AS companies,
    company_count,
    popularity,
    acceptance,
    recency
"""


def _problem_filters(
    difficulty: Optional[str],
    company: Optional[str],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    """Build a WHERE clause and its parameters from optional filters."""
    clauses: list[str] = []
    params: list[Any] = []

    if difficulty:
        clauses.append("difficulty = %s")
        params.append(difficulty.lower())
    if company:
        # Uses idx_problems_companies (GIN).
        clauses.append("companies @> ARRAY[%s]")
        params.append(company.lower())
    if search:
        clauses.append("title ILIKE %s")
        params.append(f"%{search}%")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


# --------------------------------------------------------------------- problems

def list_problems(
    limit: int = 20,
    offset: int = 0,
    difficulty: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[dict], int]:
    """Return (rows, total_matching). Ordered by popularity, the corpus ranking."""
    where, params = _problem_filters(difficulty, company, search)

    total = query_one(f"SELECT count(*) AS n FROM problems {where}", params)["n"]
    rows = query(
        f"""
        SELECT {_SUMMARY_COLS}
        FROM problems
        {where}
        ORDER BY popularity DESC, title ASC
        LIMIT %s OFFSET %s
        """,
        [*params, limit, offset],
    )
    return rows, total


def get_problem(problem_id: str) -> Optional[dict]:
    """Look up one problem by UUID or by slug. Returns None when absent."""
    # Accepting either means the frontend and the demo can use readable URLs
    # (/problems/two-sum) without a second endpoint.
    #
    # Two separate placeholders on purpose: reusing one for both the uuid and
    # the text comparison makes Postgres infer uuid from the first use, and
    # `slug = $1` then fails with "operator does not exist: text = uuid".
    # A non-UUID identifier passes NULL, and `id = NULL` is never true.
    return query_one(
        f"""
        SELECT {_SUMMARY_COLS},
               description,
               embedding IS NOT NULL AS has_embedding,
               (SELECT count(*) FROM test_cases t WHERE t.problem_id = p.id)
                   AS test_case_count
        FROM problems p
        WHERE id = %(pid)s OR slug = %(slug)s
        """,
        {"pid": _as_uuid(problem_id), "slug": problem_id},
    )


def _as_uuid(value: str):
    """Return a UUID when the string is one, else None (so `id = NULL`)."""
    from uuid import UUID

    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


# --------------------------------------------------------------------- memories

def save_memory(genome, raw_transcript: str) -> str:
    """Persist an extracted genome; returns the new memory id.

    `genome` is a schemas.memory.Genome. Its list fields map straight onto
    TEXT[] columns — psycopg adapts Python lists natively, no serialisation.
    """
    row = execute(
        """
        INSERT INTO problem_memories
            (raw_transcript, concepts, operations, constraints, objective,
             uncertainties, data_structures, algorithm_hints)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id::text AS id
        """,
        (
            raw_transcript,
            genome.concepts,
            genome.operations,
            genome.constraints,
            genome.objective,
            genome.uncertainties,
            genome.data_structures,
            genome.algorithm_hints,
        ),
    )
    return row["id"]


def get_memory(memory_id: str) -> Optional[dict]:
    """Load a stored genome. /reconstruct needs this to rebuild from memory."""
    return query_one(
        """
        SELECT id::text AS id, raw_transcript, concepts, operations,
               constraints, objective, uncertainties,
               data_structures, algorithm_hints, problem_id::text AS problem_id
        FROM problem_memories
        WHERE id = %s
        """,
        (_as_uuid(memory_id),),
    )


# -------------------------------------------------------------------- test data

def get_test_cases(problem_id: str, limit: int = 5) -> list[dict]:
    """Test cases for a problem, oldest first. Accepts a UUID or a slug.

    Capped at `limit` (default 5) — the public Judge0 CE instance is
    rate-limited, and five cases is enough to show pass/fail convincingly.
    """
    return query(
        """
        SELECT t.id::text AS id, t.input, t.expected_output
        FROM test_cases t
        JOIN problems p ON p.id = t.problem_id
        WHERE p.id = %(pid)s OR p.slug = %(slug)s
        ORDER BY t.created_at
        LIMIT %(limit)s
        """,
        {"pid": _as_uuid(problem_id), "slug": problem_id, "limit": limit},
    )


def resolve_problem_id(problem_id: str) -> Optional[str]:
    """Map a UUID-or-slug to the canonical UUID. None when no such problem."""
    row = query_one(
        "SELECT id::text AS id FROM problems WHERE id = %(pid)s OR slug = %(slug)s",
        {"pid": _as_uuid(problem_id), "slug": problem_id},
    )
    return row["id"] if row else None


def save_test_cases(problem_id: str, cases) -> int:
    """Persist generated cases. Returns how many were newly stored.

    Idempotent on (problem_id, input): generation runs once per problem ever,
    and a second visit reads from Postgres instead of spending a request.
    """
    canonical = resolve_problem_id(problem_id)
    if canonical is None or not cases:
        return 0

    stored = 0
    for case in cases:
        row = execute(
            """
            INSERT INTO test_cases (problem_id, input, expected_output)
            SELECT %(pid)s, %(input)s, %(expected)s
            WHERE NOT EXISTS (
                SELECT 1 FROM test_cases
                WHERE problem_id = %(pid)s AND input = %(input)s
            )
            RETURNING id::text AS id
            """,
            {"pid": canonical,
             "input": (case.input or "").rstrip(),
             "expected": (case.expected_output or "").rstrip()},
        )
        stored += row is not None
    return stored


def save_submission(problem_id: str, code: str, language: str, result) -> Optional[str]:
    """Record a run. `result` is a schemas.verify.VerifyResponse.

    Returns None when the problem does not exist — a submission row would
    violate the FK, and a failed audit write must not sink the user's result.
    """
    canonical = resolve_problem_id(problem_id)
    if canonical is None:
        return None

    row = execute(
        """
        INSERT INTO submissions (problem_id, code, language, status, runtime, memory)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id::text AS id
        """,
        (canonical, code, language, result.status, result.runtime, result.memory),
    )
    return row["id"]
