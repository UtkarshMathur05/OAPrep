"""Request/response models for POST /search."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.memory import Genome


class SearchRequest(BaseModel):
    memory: Genome
    memory_id: Optional[str] = None
    top_k: int = 5
    # Optional corpus filter, applied before the vector search. Lowercase slugs
    # matching data/leetcode-companywise-interview-questions/<company>/.
    companies: List[str] = Field(default_factory=list)


class Candidate(BaseModel):
    id: str
    title: str
    confidence: float
    platform: Optional[str] = None
    difficulty: Optional[str] = None
    reason: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    # Truncated for display; company_count is the true total.
    companies: List[str] = Field(default_factory=list)
    company_count: int = 0


class SearchResponse(BaseModel):
    candidates: List[Candidate]
