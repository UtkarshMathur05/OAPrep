"""Request/response models for POST /reconstruct."""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ReconstructRequest(BaseModel):
    memory_id: str
    candidate_id: str


# Where a piece of the reconstructed problem came from. Rendering this is the
# point of the product: never present an inference as something the user recalled.
Provenance = Literal["remembered", "retrieved", "inferred"]


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
    # Keyed by field name: title / description / constraints / examples.
    provenance: Dict[str, Provenance] = Field(default_factory=dict)
    # Reader-facing caveats, e.g. "You recalled obstacles; this problem has none."
    notes: List[str] = Field(default_factory=list)
    # Seeds the Monaco buffer on the Practice screen.
    starter_code: Optional[str] = None


class ReconstructResponse(BaseModel):
    problem: Problem
