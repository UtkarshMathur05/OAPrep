"""Row shape for `problems`. TODO(backend): keep in sync with database/init/01_schema.sql."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ProblemRow:
    id: str
    title: str
    description: str
    platform: Optional[str] = None
    difficulty: Optional[str] = None
    source_url: Optional[str] = None
    embedding: Optional[List[float]] = field(default=None)
    created_at: Optional[datetime] = None
