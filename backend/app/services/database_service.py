"""PostgreSQL access.

Connections come from app.db.database — do not open your own here.
Every query uses %s placeholders; never build SQL with f-strings.
"""

from typing import Any, Optional

from app.db.database import execute, query, query_one

# Ranks companies by how much of the corpus each one asks. The stored array is
# alphabetical, so slicing it raw surfaced "Accenture, Accolite, Adobe" on every
# row — true, and useless. What a reader wants from that column is the biggest
# name that asks it.
#
# Cheap enough to compute per request: unnesting 1,124 rows into ~41k pairs and
# grouping is a few milliseconds, and it stays correct as the corpus grows
# rather than freezing a hand-written list of "important" companies.
_COMPANY_RANK_CTE = """
WITH company_rank AS (
    SELECT company AS name, count(*) AS n
    FROM problems, unnest(companies) AS company
    GROUP BY company
)
"""

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
    (SELECT array_agg(c ORDER BY r.n DESC, c)
       FROM unnest(p.companies) AS c
       JOIN company_rank r ON r.name = c)[1:5]  AS companies,
    company_count,
    popularity,
    acceptance,
    recency,
    origin,
    confidence,
    contribution_count
"""


def _problem_filters(
    difficulty: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
    topic: Optional[str] = None,
    origin: Optional[str] = None,
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
    if topic:
        # Uses idx_problems_topics (GIN). Topics are stored in LeetCode's own
        # casing ("Dynamic Programming"), so the caller sends them verbatim.
        clauses.append("topics @> ARRAY[%s]")
        params.append(topic)
    if origin:
        clauses.append("origin = %s")
        params.append(origin.lower())
    if search:
        # Title or statement: browsing by remembered phrasing is the point.
        clauses.append("(title ILIKE %s OR description ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


# Whitelisted sort orders. The value is interpolated into SQL, so it can never
# come from the request directly — the API maps a key here or falls back.
_SORT_SQL = {
    "popularity": "popularity DESC, title ASC",
    "title": "title ASC",
    "difficulty": "CASE difficulty WHEN 'easy' THEN 1 WHEN 'medium' THEN 2 "
                  "WHEN 'hard' THEN 3 ELSE 4 END, popularity DESC",
    "companies": "company_count DESC, popularity DESC",
    "acceptance": "acceptance DESC NULLS LAST, popularity DESC",
    "newest": "created_at DESC, title ASC",
}


# --------------------------------------------------------------------- problems

def list_problems(
    limit: int = 20,
    offset: int = 0,
    difficulty: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
    topic: Optional[str] = None,
    origin: Optional[str] = None,
    sort: str = "popularity",
) -> tuple[list[dict], int]:
    """Return (rows, total_matching). Ordered by popularity, the corpus ranking."""
    where, params = _problem_filters(difficulty, company, search, topic, origin)
    order = _SORT_SQL.get(sort, _SORT_SQL["popularity"])

    total = query_one(f"SELECT count(*) AS n FROM problems p {where}", params)["n"]
    rows = query(
        f"""
        {_COMPANY_RANK_CTE}
        SELECT {_SUMMARY_COLS}
        FROM problems p
        {where}
        ORDER BY {order}
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
        {_COMPANY_RANK_CTE}
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


# ----------------------------------------------------------------------- facets

# Ceilings on the facet lists. 660 companies and ~70 topics are more than a nav
# rail can show; the tail is a long drizzle of one-problem companies that adds
# scrolling, not information.
FACET_COMPANY_LIMIT = 80
FACET_TOPIC_LIMIT = 40


def facets() -> dict:
    """Counts for every browse axis, in one round trip per axis.

    `unnest` over the arrays rather than a lookup table: the corpus is 1,124
    rows, so grouping the flattened arrays is a few milliseconds and saves two
    tables that would need keeping in sync with the dump.
    """
    companies = query(
        """
        SELECT company AS name, count(*) AS count
        FROM problems, unnest(companies) AS company
        GROUP BY company
        ORDER BY count DESC, company ASC
        LIMIT %s
        """,
        [FACET_COMPANY_LIMIT],
    )
    topics = query(
        """
        SELECT topic AS name, count(*) AS count
        FROM problems, unnest(topics) AS topic
        GROUP BY topic
        ORDER BY count DESC, topic ASC
        LIMIT %s
        """,
        [FACET_TOPIC_LIMIT],
    )
    # Ordered easy -> hard rather than by count; a difficulty filter that
    # reorders itself as the corpus changes reads as a bug.
    difficulties = query(
        """
        SELECT difficulty AS name, count(*) AS count
        FROM problems
        WHERE difficulty IS NOT NULL
        GROUP BY difficulty
        ORDER BY CASE difficulty
                     WHEN 'easy' THEN 1 WHEN 'medium' THEN 2 WHEN 'hard' THEN 3
                     ELSE 4 END
        """
    )
    totals = query_one(
        """
        SELECT count(*) AS problems,
               count(*) FILTER (WHERE origin = 'community') AS community,
               (SELECT count(DISTINCT company)
                  FROM problems, unnest(companies) AS company) AS companies,
               (SELECT count(DISTINCT topic)
                  FROM problems, unnest(topics) AS topic) AS topics
        FROM problems
        """
    )
    return {
        "companies": companies,
        "topics": topics,
        "difficulties": difficulties,
        "totals": totals,
    }


# ----------------------------------------------------------- contributions

# A single unverified account of a problem. Deliberately low: the UI labels
# anything under 0.5 as unverified, and the number has to be able to grow.
SEED_CONFIDENCE = 0.35
# Each independent corroboration is worth this much...
CONFIRMATION_STEP = 0.15
# ...up to a ceiling. Community memory never becomes as trustworthy as a
# problem statement we actually fetched from LeetCode, so it never reaches 1.0.
MAX_COMMUNITY_CONFIDENCE = 0.95


def community_confidence(contribution_count: int) -> float:
    """Confidence for a community problem described `contribution_count` times.

    One account: 0.35. Every further independent description adds 0.15, capped
    at 0.95. Linear on purpose — it has to be explainable in one sentence.
    """
    if contribution_count <= 0:
        return SEED_CONFIDENCE
    raw = SEED_CONFIDENCE + CONFIRMATION_STEP * (contribution_count - 1)
    return round(min(raw, MAX_COMMUNITY_CONFIDENCE), 2)


def create_community_problem(
    *,
    slug: str,
    title: str,
    description: str,
    difficulty: Optional[str],
    topics: list[str],
    companies: list[str],
    embedding: Optional[list[float]],
) -> dict:
    """Insert a user-described problem and return its summary row.

    Slug collisions are resolved by suffixing rather than upserting: two people
    describing "sliding window thing" are not necessarily describing the same
    problem, and silently merging them would corrupt the confidence signal.
    """
    unique = slug
    n = 2
    while query_one("SELECT 1 AS x FROM problems WHERE slug = %s", [unique]):
        unique = f"{slug}-{n}"
        n += 1

    row = query_one(
        """
        INSERT INTO problems (
            slug, title, description, platform, difficulty, topics, companies,
            company_count, embedding, description_source,
            origin, confidence, contribution_count
        )
        VALUES (
            %(slug)s, %(title)s, %(description)s, 'community', %(difficulty)s,
            %(topics)s, %(companies)s, %(company_count)s, %(embedding)s,
            -- contribution_count starts at 0: record_contribution() is what
            -- counts the author, so seeding it here would count them twice.
            'community', 'community', %(confidence)s, 0
        )
        RETURNING id::text AS id, slug
        """,
        {
            "slug": unique,
            "title": title,
            "description": description,
            "difficulty": (difficulty or None),
            "topics": topics,
            "companies": [c.lower() for c in companies],
            "company_count": len(companies),
            "embedding": embedding,
            "confidence": SEED_CONFIDENCE,
        },
    )
    return row


def record_contribution(
    problem_id: str,
    *,
    kind: str,
    transcript: str,
    details: Optional[dict] = None,
) -> dict:
    """Log a contribution and return the problem's new confidence.

    Only community problems move: a corpus problem's statement came from
    LeetCode, so a user agreeing with it is not new evidence. The contribution
    is still recorded — it is the signal that tells us which corpus problems
    people actually half-remember.
    """
    import json

    execute(
        """
        INSERT INTO contributions (problem_id, kind, transcript, details)
        VALUES (%s, %s, %s, %s::jsonb)
        """,
        [_as_uuid(problem_id), kind, transcript, json.dumps(details or {})],
    )

    row = query_one(
        """
        UPDATE problems
        SET contribution_count = contribution_count + 1
        WHERE id = %s
        RETURNING id::text AS id, origin, contribution_count
        """,
        [_as_uuid(problem_id)],
    )
    if row is None:
        return {"confidence": 0.0, "contribution_count": 0}

    if row["origin"] != "community":
        return {
            "confidence": 1.0,
            "contribution_count": row["contribution_count"],
        }

    confidence = community_confidence(row["contribution_count"])
    execute("UPDATE problems SET confidence = %s WHERE id = %s",
            [confidence, _as_uuid(problem_id)])
    return {"confidence": confidence, "contribution_count": row["contribution_count"]}
