"""Bridge from the API layer to the `ai/` package.

USE_MOCK_AI=true still returns canned data, so the frontend can integrate with
the backend down. With it false we call the real ai.* modules, and any failure
degrades to a useful message rather than a 500 (CLAUDE.md §20).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from app.config import GEMINI_API_KEY, USE_MOCK_AI
from app.schemas.memory import Genome, MemoryRequest, MemoryResponse
from app.schemas.reconstruct import Problem, ReconstructRequest, ReconstructResponse
from app.schemas.search import Candidate, SearchRequest, SearchResponse
from app.services import database_service

log = logging.getLogger(__name__)

# Judge0 runs a script over stdin/stdout (§9), so a blank editor is a worse
# starting point than a skeleton that already reads input the right way. Used
# whenever the model returns no starter_code, which it currently never does —
# the reconstruction prompt does not ask for one.
_STARTER_PY = """import sys

def solve(data):
    # data is the whitespace-split stdin, as strings.
    # TODO: your solution here
    return 0

def main():
    data = sys.stdin.read().split()
    print(solve(data))

if __name__ == "__main__":
    main()
"""


def _mock_genome() -> Genome:
    """Canned genome for mock mode and for a teammate with no API key."""
    return Genome(
        concepts=["grid", "dynamic programming"],
        operations=["move right", "move down"],
        objective="minimize cost",
        uncertainties=["obstacles"],
    )


def _genome_for(memory_id: str):
    """Rehydrate a stored genome from problem_memories, or None.

    Postgres is the source of truth: api/memory.py persists the genome and
    returns that row's id, so /reconstruct must read it back from there. An
    in-process dict keyed by a locally minted uuid could never match.
    """
    from ai.models.problem_genome import ProblemGenome
    from app.services import database_service

    row = database_service.get_memory(memory_id) if memory_id else None
    if row is None:
        return None
    return ProblemGenome(**{
        k: row[k] for k in ("concepts", "operations", "constraints", "objective",
                            "uncertainties", "data_structures", "algorithm_hints")
    })


def _genome_from(schema_genome: Genome):
    from ai.models.problem_genome import ProblemGenome

    return ProblemGenome(**schema_genome.model_dump())


def extract_memory(req: MemoryRequest) -> MemoryResponse:
    """Transcript -> Genome. api/memory.py persists the result and sets
    memory_id, so nothing is stored here."""
    if USE_MOCK_AI or not GEMINI_API_KEY:
        return MemoryResponse(memory_id=None, memory=_mock_genome())

    from ai.extraction.genome import extract_genome
    from ai.gemini_client import AIError

    if not (req.transcript or "").strip():
        raise HTTPException(400, "Tell us what you remember first.")

    try:
        genome = extract_genome(req.transcript)
    except AIError as exc:
        log.warning("extraction failed: %s", exc)
        raise HTTPException(503, "We couldn't read that memory just now. Try again in a moment.")

    return MemoryResponse(memory_id=None, memory=Genome(**genome.model_dump()))


def search_candidates(req: SearchRequest) -> SearchResponse:
    if USE_MOCK_AI:
        return SearchResponse(candidates=[
            Candidate(id="1", title="Minimum Path Sum", confidence=0.91, difficulty="medium"),
            Candidate(id="2", title="Unique Paths", confidence=0.72, difficulty="medium"),
        ])

    from ai.db import DBError
    from ai.retrieval.reranker import rerank
    from ai.retrieval.vector_search import search_candidates as vector_search

    genome = _genome_from(req.memory)
    if genome.is_empty():
        raise HTTPException(400, "That memory is too vague to search on. Add another detail.")

    try:
        # Retrieve wider than we return: reranking needs room to reorder.
        found = vector_search(genome, top_k=max(req.top_k * 2, 10), companies=req.companies)
    except DBError as exc:
        log.warning("vector search failed: %s", exc)
        raise HTTPException(503, "The problem database is unavailable.")

    if not found:
        raise HTTPException(
            404, "We couldn't confidently identify the problem. Try adding another detail.")

    ranked = rerank(genome, found)[: req.top_k]
    return SearchResponse(candidates=[
        Candidate(
            id=c.id, title=c.title, confidence=round(c.confidence, 3),
            platform=c.platform, difficulty=c.difficulty, reason=c.reason,
            topics=c.topics, companies=c.companies, company_count=c.company_count,
        )
        for c in ranked
    ])


def reconstruct(req: ReconstructRequest) -> ReconstructResponse:
    if USE_MOCK_AI:
        return ReconstructResponse(problem=Problem(
            id=req.candidate_id,
            title="Minimum Path Sum",
            description="Given an m x n grid of non-negative numbers, find a path "
                        "from top-left to bottom-right that minimizes the sum along "
                        "the path. You may only move down or right.",
            constraints=["1 <= m, n <= 200", "0 <= grid[i][j] <= 200"],
            confidence=0.91,
            provenance={
                "title": "retrieved",
                "description": "retrieved",
                "constraints": "inferred",
                "examples": "inferred",
            },
            notes=[
                "You weren't sure about obstacles; this problem has none.",
                "Constraints were not in your memory and come from the original problem.",
            ],
            starter_code=(
                "import sys\n\n"
                "def main():\n"
                "    data = sys.stdin.read().split()\n"
                "    # your solution here\n"
                "    print(0)\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n"
            ),
        ))

    from ai.db import DBError
    from ai.models.problem_genome import ProblemGenome
    from ai.reconstruction.reconstruct import reconstruct_problem
    from ai.retrieval.vector_search import get_candidate

    try:
        candidate = get_candidate(req.candidate_id)
    except DBError as exc:
        log.warning("candidate lookup failed: %s", exc)
        raise HTTPException(503, "The problem database is unavailable.")
    if candidate is None:
        raise HTTPException(404, f"No problem with id {req.candidate_id!r}.")

    # Load the genome the route persisted. A miss is recoverable: reconstruct
    # from the candidate alone rather than refusing — it only costs the
    # memory-specific notes.
    genome = _genome_for(req.memory_id) or ProblemGenome()

    problem = reconstruct_problem(genome, candidate)

    # The reconstruction's examples are already stdin/stdout pairs, so they are
    # test cases. Storing them costs nothing and means Run tests works for any
    # problem the user actually reached, without a second model call.
    try:
        from ai.verification.test_generator import cases_from_examples

        database_service.save_test_cases(candidate.id, cases_from_examples(problem))
    except Exception as exc:  # noqa: BLE001 - never fail a reconstruction over this
        log.warning("could not store examples as test cases: %s", exc)

    return ReconstructResponse(problem=Problem(
        id=candidate.id,
        title=problem.title,
        description=problem.description,
        constraints=problem.constraints,
        # The ai models use WorkedExample / ProblemProvenance rather than the
        # dicts this schema takes: Gemini rejects `additionalProperties` in a
        # response schema, so a free-form Dict[str, Provenance] cannot be used
        # there. They serialise identically, so convert at the boundary.
        examples=[e.model_dump() for e in problem.examples],
        confidence=round(problem.confidence or candidate.confidence, 3),
        provenance=problem.provenance.model_dump(),
        notes=problem.notes,
        starter_code=problem.starter_code or _STARTER_PY,
    ))
