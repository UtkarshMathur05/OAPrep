"""Request/response models for POST /verify."""

from typing import List, Optional
from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    problem_id: str
    code: str
    language: str


class TestResult(BaseModel):
    index: int
    passed: bool
    input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None


class VerifyResponse(BaseModel):
    status: str
    passed: int
    total: int
    runtime: Optional[str] = None
    memory: Optional[str] = None
    results: List[TestResult] = Field(default_factory=list)
