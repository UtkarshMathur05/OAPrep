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

def get_test_cases(problem_id: str, limit: int = 5):
    """TODO(backend): task B6. Capped at the Judge0 ceiling."""
    raise NotImplementedError


def save_submission(problem_id: str, code: str, language: str, result) -> str:
    """TODO(backend): task B6."""
    raise NotImplementedError
