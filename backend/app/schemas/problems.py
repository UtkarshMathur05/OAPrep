"""Schemas for the corpus browse endpoints.

Deliberately separate from `reconstruct.Problem`. A corpus row and a
reconstructed problem are different things: `constraints`, `examples` and
`confidence` are produced by Gemini at reconstruct/rerank time and are not
columns, so a listing must not promise them.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ProblemSummary(BaseModel):
    """One row of the known-problem corpus."""

    id: str
    slug: str
    title: str
    difficulty: Optional[str] = None
    platform: Optional[str] = None
    source_url: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    # Truncated for display; company_count is the real total.
    companies: List[str] = Field(default_factory=list)
    company_count: int = 0
    popularity: float = 0.0
    acceptance: Optional[float] = None
    recency: Optional[str] = None


class ProblemDetail(ProblemSummary):
    """A single corpus row, including its statement."""

    description: str
    has_embedding: bool = False
    test_case_count: int = 0


class ProblemListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    problems: List[ProblemSummary]
