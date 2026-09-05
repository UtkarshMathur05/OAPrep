"""Row shapes for `submissions` and `test_cases`."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SubmissionRow:
    id: str
    problem_id: str
    code: str
    language: str
    status: Optional[str] = None
    runtime: Optional[str] = None
    memory: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class TestCaseRow:
    id: str
    problem_id: str
    input: str
    expected_output: str
    created_at: Optional[datetime] = None
