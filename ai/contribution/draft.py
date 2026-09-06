"""Turn a user's description of a problem we do not have into a corpus row.

This is the inverse of reconstruction. Reconstruction starts from a known
problem and bends it toward a memory; drafting has no known problem at all, so
everything it produces is `inferred` by definition. That is why the row it
writes starts at a low confidence rather than joining the corpus as fact
(CLAUDE.md §16, "honest gaps over confident fabrication").

The model is asked to stay close to what the user actually said and to leave
fields empty rather than invent them.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from pydantic import BaseModel, Field

from ai.gemini_client import AIError, generate_structured
from ai.models.problem_genome import WorkedExample

log = logging.getLogger(__name__)

_TRANSCRIPT_CHARS = 4000


class DraftedProblem(BaseModel):
    """A problem statement written from a user's description alone."""

    title: str = ""
    description: str = ""
    difficulty: str = ""          # easy | medium | hard | "" when unclear
    topics: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    examples: List[WorkedExample] = Field(default_factory=list)
    # What the user never said and the model filled in. Rendered to the
    # contributor so they can correct it before it is stored.
    assumptions: List[str] = Field(default_factory=list)


_PROMPT = """A user is describing a coding problem that is missing from our
database. Write it up as a clean problem statement.

Rules:
- Stay close to what they said. Do not add a twist, a follow-up part, or an
  extra constraint they never mentioned.
- Anything you had to decide yourself goes in "assumptions", one short line
  each. Constraints and complexity targets almost always belong there.
- "topics" are algorithm/data-structure tags in title case, e.g.
  "Dynamic Programming", "Hash Table". At most four.
- "difficulty" is exactly "easy", "medium" or "hard", or "" if you cannot tell.
- Examples are literal stdin/stdout text. "input" is what a solution reads from
  stdin; "output" is what it prints. Never JSON array syntax like [[1,2],[3,4]].
  Pick the simplest whitespace-separated shape - sizes first, then values - and
  use the same shape in every example. Omit examples entirely rather than
  guessing a format that contradicts what they described.
- The description must not mention the user, this system, or uncertainty. Write
  it the way a problem set would.

WHAT THEY REMEMBER:
{transcript}

{details}
"""


def _details_block(details: dict) -> str:
    """Render the follow-up answers, skipping the ones left blank."""
    labels = [
        ("title", "Their working title"),
        ("difficulty", "Difficulty they recall"),
        ("topics", "Topics they recall"),
        ("companies", "Where it was asked"),
        ("input_format", "Input format"),
        ("output_format", "Output format"),
        ("example", "An example they remember"),
        ("constraints", "Constraints they recall"),
    ]
    lines = []
    for key, label in labels:
        value = details.get(key)
        if isinstance(value, list):
            value = ", ".join(v for v in value if v)
        if value and str(value).strip():
            lines.append(f"{label}: {str(value).strip()}")
    if not lines:
        return "They gave no further details."
    return "THEY ALSO TOLD US:\n" + "\n".join(lines)


def draft_problem(transcript: str, details: Optional[dict] = None) -> DraftedProblem:
    """Draft a problem statement. Raises AIError if Gemini cannot be reached."""
    prompt = _PROMPT.format(
        transcript=(transcript or "").strip()[:_TRANSCRIPT_CHARS],
        details=_details_block(details or {}),
    )
    drafted = generate_structured(prompt, DraftedProblem)

    # The model's own answers win over ours, but a user-supplied title is a
    # deliberate choice and should not be paraphrased away.
    supplied_title = (details or {}).get("title")
    if supplied_title and supplied_title.strip():
        drafted.title = supplied_title.strip()

    drafted.title = drafted.title.strip() or "Untitled problem"
    drafted.difficulty = drafted.difficulty.strip().lower()
    if drafted.difficulty not in {"easy", "medium", "hard"}:
        drafted.difficulty = ""
    return drafted


def slugify(title: str) -> str:
    """LeetCode-style slug. The corpus keys on these, so keep the shape."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (slug or "untitled")[:80]


def embedding_text(title: str, description: str, topics: List[str],
                   difficulty: str = "") -> str:
    """What we embed for a community problem.

    Byte-for-byte the same shape as `ai/corpus/load_corpus.embed_text_for`. A
    different layout would put contributed problems in a slightly different
    region of the space, and they would never surface next to corpus rows in
    recall — the one thing contributing is for.
    """
    return (f"{title}\nTopics: {', '.join(topics)}\n"
            f"Difficulty: {difficulty or None}\n\n{description[:4000]}")
