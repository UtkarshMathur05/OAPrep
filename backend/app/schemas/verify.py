"""Request/response models for POST /verify."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    problem_id: str
    code: str
    language: str = "python"
    # 'run' is a trial; 'submit' is the user claiming the solution is finished.
    # Only an accepted submit marks a problem complete — a passing run is not
    # the same statement, and conflating them takes the decision off the user.
    kind: Literal["run", "submit"] = "run"


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

    # --- outcome ---------------------------------------------------------
    submission_id: Optional[str] = None
    kind: str = "run"
    all_passed: bool = False

    # --- this session's standing on this problem, after the call ---------
    # Returned inline so the editor never has to follow a result with a second
    # request just to redraw its own counters.
    solved: bool = False
    runs: int = 0
    submissions: int = 0


class ProblemProgress(BaseModel):
    """One problem, from the current session's point of view."""

    runs: int = 0
    submissions: int = 0
    solved: bool = False
    best_passed: int = 0
    total: int = 0


class SessionProgress(BaseModel):
    """Everything the current session has touched, for marking a listing."""

    solved: List[str] = Field(default_factory=list)
    attempted: List[str] = Field(default_factory=list)
    runs: int = 0
    solved_count: int = 0


class LanguageOut(BaseModel):
    id: str
    label: str
    monaco: str
    starter: str
