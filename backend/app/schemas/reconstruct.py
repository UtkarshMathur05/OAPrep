"""Request/response models for POST /reconstruct."""

from typing import List, Optional
from pydantic import BaseModel, Field


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


class ReconstructResponse(BaseModel):
    problem: Problem
