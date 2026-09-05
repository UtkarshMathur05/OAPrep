"""Step 4 — Semantic retrieval over problems.embedding (pgvector).

TODO(ai): query with `ORDER BY embedding <=> %s LIMIT k` and map rows to
ProblemCandidate.
"""

from typing import List

from ai.models.problem_genome import ProblemCandidate, ProblemGenome


def search_candidates(genome: ProblemGenome, top_k: int = 10) -> List[ProblemCandidate]:
    raise NotImplementedError
