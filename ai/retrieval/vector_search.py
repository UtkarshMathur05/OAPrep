"""Step 4 — Semantic retrieval over problems.embedding (pgvector).

Exact cosine scan, no ANN index: at ~1,100 rows it is a couple of milliseconds
and an ivfflat index with the usual lists=100 measurably hurts recall.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from ai import db
from ai.models.problem_genome import ProblemCandidate, ProblemGenome
from ai.retrieval.embeddings import embed_text

# `<=>` is cosine distance in [0, 2]; similarity = 1 - distance.
_SQL = """
SELECT id::text, slug, title, description, difficulty, source_url,
       topics, companies, company_count, popularity,
       1 - (embedding <=> %(vec)s::vector) AS similarity
FROM problems
WHERE embedding IS NOT NULL
  {company_filter}
ORDER BY embedding <=> %(vec)s::vector
LIMIT %(k)s
"""

# `&&` is overlap: "asked at ANY of these companies", which is what a user means
# by "it was a Google or Amazon question". `@>` would demand all of them at once.
_COMPANY_FILTER = "AND companies && %(companies)s::text[]"

# Truncated for display; company_count carries the real total.
_MAX_COMPANIES_SHOWN = 6


def search_candidates(
    genome: ProblemGenome,
    top_k: int = 10,
    companies: Optional[Sequence[str]] = None,
) -> List[ProblemCandidate]:
    """Retrieve the problems whose text sits closest to the remembered genome.

    Returns [] for an empty genome rather than embedding the empty string, and
    lets ai.db.DBError propagate so the caller can show a real message (§20).
    """
    query_text = genome.to_query_text()
    if not query_text:
        return []

    params = {"vec": str(embed_text(query_text)), "k": max(1, top_k)}
    company_filter = ""
    if companies:
        # Corpus stores lowercase slugs (data/leetcode-companywise-.../<company>).
        params["companies"] = [c.strip().lower() for c in companies if c and c.strip()]
        if params["companies"]:
            company_filter = _COMPANY_FILTER

    rows = db.query(_SQL.format(company_filter=company_filter), params)

    return [
        ProblemCandidate(
            id=row[0],
            slug=row[1],
            title=row[2],
            # Raw cosine similarity. The reranker replaces this with a judged
            # score; it is only the fallback ordering if reranking fails.
            confidence=max(0.0, min(1.0, float(row[10]))),
            description=row[3],
            platform="leetcode",
            difficulty=row[4],
            source_url=row[5],
            topics=list(row[6] or []),
            companies=list(row[7] or [])[:_MAX_COMPANIES_SHOWN],
            company_count=int(row[8] or 0),
            popularity=float(row[9] or 0.0),
        )
        for row in rows
    ]
