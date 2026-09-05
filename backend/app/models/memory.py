"""Row shape for `problem_memories`."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class MemoryRow:
    id: str
    raw_transcript: str
    problem_id: Optional[str] = None
    concepts: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    objective: Optional[str] = None
    uncertainties: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
