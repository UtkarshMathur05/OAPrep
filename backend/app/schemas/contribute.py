"""Schemas for the contribution flow.

Two steps, because the interesting case is the first one. A user describing a
problem we already have should be told so — that is the recall pipeline doing
its job — rather than silently seeding a duplicate. Only when nothing matches
do we ask follow-up questions and write a new row.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.memory import Genome
from app.schemas.search import Candidate


class ContributeMatchRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    top_k: int = 5


class ContributeMatchResponse(BaseModel):
    """What we think the user is describing, before they commit to anything."""

    memory_id: Optional[str] = None
    memory: Genome
    candidates: List[Candidate] = Field(default_factory=list)
    # True when the best candidate is close enough that a new row would very
    # likely be a duplicate. The UI defaults to "confirm this one" in that case.
    likely_duplicate: bool = False


class ContributeDetails(BaseModel):
    """The follow-up answers. Every field is optional — a partial memory is
    still worth recording, and the draft step fills gaps as `inferred`."""

    title: Optional[str] = None
    difficulty: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    companies: List[str] = Field(default_factory=list)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    example: Optional[str] = None
    constraints: Optional[str] = None


class ContributeRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    details: ContributeDetails = Field(default_factory=ContributeDetails)
    # Set when the user picked one of the match candidates instead: we record
    # the corroboration and raise that problem's confidence.
    confirm_problem_id: Optional[str] = None


class ContributeResponse(BaseModel):
    problem_id: str
    slug: str
    title: str
    # 'created' -> a new community problem; 'confirmed' -> an existing one.
    action: str
    confidence: float
    contribution_count: int
    test_case_count: int = 0
    message: str = ""
