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
    # 'corpus' (shipped with the LeetCode dump) or 'community' (user-described).
    origin: str = "corpus"
    # 1.0 for corpus rows; a community row earns its way up from 0.35 as more
    # people independently describe the same problem.
    confidence: float = 1.0
    contribution_count: int = 0


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


class Facet(BaseModel):
    """One value of a browse axis, with how many problems carry it."""

    name: str
    count: int


class FacetTotals(BaseModel):
    problems: int = 0
    community: int = 0
    companies: int = 0
    topics: int = 0


class FacetsResponse(BaseModel):
    """Everything the browse navigation needs, in one request."""

    companies: List[Facet] = Field(default_factory=list)
    topics: List[Facet] = Field(default_factory=list)
    difficulties: List[Facet] = Field(default_factory=list)
    totals: FacetTotals = Field(default_factory=FacetTotals)
