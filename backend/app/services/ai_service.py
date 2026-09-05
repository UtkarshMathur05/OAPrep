"""Bridge from the API layer to the `ai/` package.

While USE_MOCK_AI is true this returns canned data, so the frontend and backend
can integrate before the AI modules land.
TODO(backend): call ai.extraction / ai.retrieval / ai.reconstruction when ready.
"""

from app.config import GEMINI_API_KEY, USE_MOCK_AI
from app.schemas.memory import Genome, MemoryRequest, MemoryResponse
from app.schemas.reconstruct import Problem, ReconstructRequest, ReconstructResponse
from app.schemas.search import Candidate, SearchRequest, SearchResponse


def _mock_genome() -> Genome:
    return Genome(
        concepts=["grid", "dynamic programming"],
        operations=["move right", "move down"],
        objective="minimize cost",
        uncertainties=["obstacles"],
    )


def extract_memory(req: MemoryRequest) -> MemoryResponse:
    """Transcript -> Problem Genome, via ai.extraction.

    Falls back to the mock when USE_MOCK_AI is set or no key is configured, so
    a teammate without a key still gets a correctly shaped response.
    """
    if USE_MOCK_AI or not GEMINI_API_KEY:
        return MemoryResponse(memory_id=None, memory=_mock_genome())

    # Imported lazily: `ai` pulls in google-genai, and a teammate running in
    # mock mode should never pay that import cost or need the package.
    from ai.extraction.genome import extract_genome

    genome = extract_genome(req.transcript)
    # ProblemGenome (ai) and Genome (api schema) carry the same seven fields;
    # round-tripping through a dict keeps the two models decoupled.
    return MemoryResponse(memory_id=None, memory=Genome(**genome.model_dump()))


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
                "class Solution:\n"
                "    def minPathSum(self, grid: list[list[int]]) -> int:\n"
                "        pass\n"
            ),
        ))
    raise NotImplementedError
