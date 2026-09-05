"""The Problem Genome: what the user actually remembers, before we guess."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ProblemGenome(BaseModel):
    """Structured representation of a fuzzy memory of a coding problem.

    Everything is optional-ish on purpose: a vague memory yields a sparse
    genome, and that sparseness is signal for the retrieval step.
    """

    concepts: List[str] = Field(default_factory=list)
    operations: List[str] = Field(default_factory=list)
    objective: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    data_structures: List[str] = Field(default_factory=list)
    algorithm_hints: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)

    def to_query_text(self) -> str:
        """Flatten the genome into text suitable for embedding."""
        parts = [
            " ".join(self.concepts),
            " ".join(self.operations),
            self.objective or "",
            " ".join(self.data_structures),
            " ".join(self.algorithm_hints),
            " ".join(self.constraints),
        ]
        return " ".join(p for p in parts if p).strip()


class ProblemCandidate(BaseModel):
    """A known problem proposed as a match for a genome."""

    id: str
    title: str
    confidence: float = 0.0
    description: Optional[str] = None
    platform: Optional[str] = None
    difficulty: Optional[str] = None
    source_url: Optional[str] = None
    reason: Optional[str] = None


class ReconstructedProblem(BaseModel):
    """A full problem statement rebuilt from a candidate + the user's memory."""

    title: str
    description: str
    constraints: List[str] = Field(default_factory=list)
    examples: List[dict] = Field(default_factory=list)
    confidence: float = 0.0


class TestCase(BaseModel):
    input: str
    expected_output: str
    explanation: Optional[str] = None
