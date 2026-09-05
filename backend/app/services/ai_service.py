"""Bridge from the API layer to the `ai/` package.

USE_MOCK_AI=true still returns canned data, so the frontend can integrate with
the backend down. With it false we call the real ai.* modules, and any failure
degrades to a useful message rather than a 500 (CLAUDE.md §20).
"""

from __future__ import annotations

import logging
from typing import Dict
from uuid import uuid4

from fastapi import HTTPException

from app.config import USE_MOCK_AI
from app.schemas.memory import Genome, MemoryRequest, MemoryResponse
from app.schemas.reconstruct import Problem, ReconstructRequest, ReconstructResponse
from app.schemas.search import Candidate, SearchRequest, SearchResponse

log = logging.getLogger(__name__)

# Genomes live here between POST /memory and POST /reconstruct.
# TODO(backend): replace with the problem_memories table; this is per-process
# and does not survive a reload, which is fine for a demo and not for anything else.
_MEMORIES: Dict[str, "object"] = {}


def _genome_from(schema_genome: Genome):
    from ai.models.problem_genome import ProblemGenome

    return ProblemGenome(**schema_genome.model_dump())


def extract_memory(req: MemoryRequest) -> MemoryResponse:
    if USE_MOCK_AI:
        return MemoryResponse(
            memory_id="mock-memory-1",
            memory=Genome(
                concepts=["grid", "dynamic programming"],
                operations=["move right", "move down"],
                objective="minimize cost",
                uncertainties=["obstacles"],
            ),
        )

    from ai.extraction.genome import extract_genome
    from ai.gemini_client import AIError

    if not (req.transcript or "").strip():
        raise HTTPException(400, "Tell us what you remember first.")

    try:
        genome = extract_genome(req.transcript)
    except AIError as exc:
        log.warning("extraction failed: %s", exc)
        raise HTTPException(503, "We couldn't read that memory just now. Try again in a moment.")

    memory_id = uuid4().hex
    _MEMORIES[memory_id] = genome
    return MemoryResponse(memory_id=memory_id, memory=Genome(**genome.model_dump()))


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

    # A missing genome is recoverable: reconstruct from the candidate alone
    # rather than refusing. It only costs the memory-specific notes.
    genome = _MEMORIES.get(req.memory_id) or ProblemGenome()

    problem = reconstruct_problem(genome, candidate)
    return ReconstructResponse(problem=Problem(
        id=candidate.id,
        title=problem.title,
        description=problem.description,
        constraints=problem.constraints,
        examples=problem.examples,
        confidence=round(problem.confidence or candidate.confidence, 3),
        provenance=problem.provenance,
        notes=problem.notes,
        starter_code=problem.starter_code,
    ))
