"""Request/response models for POST /reconstruct."""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# How a given part of the reconstructed problem came to be known.
#   remembered — the user said it
#   retrieved  — it came from the stored corpus row
#   inferred   — the model supplied it; the user never said it
# CLAUDE.md §19: an inference must never be presented as a remembered fact.
Provenance = Literal["remembered", "retrieved", "inferred"]


class ReconstructRequest(BaseModel):
    memory_id: str
    candidate_id: str


class Example(BaseModel):
    input: str
    output: str
    explanation: Optional[str] = None


class Problem(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    constraints: List[str] = Field(default_factory=list)
    examples: List[Example] = Field(default_factory=list)
    confidence: float = 0.0

    # Field name -> how that field was arrived at. Expected keys are this
    # model's own content fields: "title", "description", "constraints",
    # "examples". A missing key means the pipeline made no claim; the UI
    # should render that as unlabelled rather than guessing.
    provenance: Dict[str, Provenance] = Field(default_factory=dict)
    # Human-readable caveats for Screen 4, e.g. "You mentioned obstacles, but
    # the matched problem has none."
    notes: List[str] = Field(default_factory=list)
    # Seeds the Monaco buffer on the Practice screen. Python only (see §9).
    starter_code: Optional[str] = None


class ReconstructResponse(BaseModel):
    problem: Problem
