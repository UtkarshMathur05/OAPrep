"""Request/response models for POST /search."""

from typing import List, Optional
from pydantic import BaseModel

from app.schemas.memory import Genome


class SearchRequest(BaseModel):
    memory: Genome
    memory_id: Optional[str] = None
    top_k: int = 5


class Candidate(BaseModel):
    id: str
    title: str
    confidence: float
    platform: Optional[str] = None
    difficulty: Optional[str] = None
    reason: Optional[str] = None


class SearchResponse(BaseModel):
    candidates: List[Candidate]
