"""Request/response models for POST /memory."""

from typing import List, Optional
from pydantic import BaseModel, Field


class MemoryRequest(BaseModel):
    transcript: str


class Genome(BaseModel):
    concepts: List[str] = Field(default_factory=list)
    operations: List[str] = Field(default_factory=list)
    objective: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    data_structures: List[str] = Field(default_factory=list)
    algorithm_hints: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)


class MemoryResponse(BaseModel):
    memory_id: Optional[str] = None
    memory: Genome
