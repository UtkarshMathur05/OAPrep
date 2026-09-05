"""Bridge from the API layer to the `ai/` package.

While USE_MOCK_AI is true this returns canned data, so the frontend and backend
can integrate before the AI modules land.
TODO(backend): call ai.extraction / ai.retrieval / ai.reconstruction when ready.
"""

from app.config import USE_MOCK_AI
from app.schemas.memory import Genome, MemoryRequest, MemoryResponse
from app.schemas.reconstruct import Problem, ReconstructRequest, ReconstructResponse
from app.schemas.search import Candidate, SearchRequest, SearchResponse


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
    raise NotImplementedError


def search_candidates(req: SearchRequest) -> SearchResponse:
    if USE_MOCK_AI:
        return SearchResponse(candidates=[
            Candidate(id="1", title="Minimum Path Sum", confidence=0.91, difficulty="medium"),
            Candidate(id="2", title="Unique Paths", confidence=0.72, difficulty="medium"),
        ])
    raise NotImplementedError


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
    raise NotImplementedError
