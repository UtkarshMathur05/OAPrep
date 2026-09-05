"""Step 5 — LLM reranking of retrieved candidates.

Vector similarity alone bunches everything into a narrow band (0.78 vs 0.73 for
a good match versus a bad one), which is both a poor ordering signal and an
unreadable confidence bar. One Gemini call over the whole shortlist judges how
well each candidate actually explains the memory, and spreads the scores.

Degrades to retrieval order if the call fails — a worse ordering beats no
candidates at all (CLAUDE.md §20).
"""

from __future__ import annotations

import json
import logging
from typing import List

from pydantic import BaseModel, Field

from ai.gemini_client import AIError, generate_structured, load_prompt
from ai.models.problem_genome import ProblemCandidate, ProblemGenome

log = logging.getLogger(__name__)

# Enough of the statement to judge the match; short enough to keep the prompt
# small, which matters on a 20-requests-per-day free tier.
_DESCRIPTION_CHARS = 600
# Confidences within this band count as a tie, broken by popularity.
_TIE_BAND = 0.05


class RerankedCandidate(BaseModel):
    id: str
    confidence: float = 0.0
    reason: str = ""


class RerankResponse(BaseModel):
    candidates: List[RerankedCandidate] = Field(default_factory=list)


def _sort_key(candidate: ProblemCandidate):
    """Confidence first; popularity breaks near-ties.

    Between two problems that fit the memory equally well, the one 126 companies
    ask is the likelier thing to have been remembered.
    """
    banded = round(candidate.confidence / _TIE_BAND)
    return (-banded, -candidate.popularity, -candidate.confidence)


def rerank(genome: ProblemGenome, candidates: List[ProblemCandidate]) -> List[ProblemCandidate]:
    """Reorder candidates by how well each explains the genome."""
    if not candidates:
        return []

    payload = [
        {
            "id": c.id,
            "title": c.title,
            "difficulty": c.difficulty,
            "topics": c.topics,
            "description": (c.description or "")[:_DESCRIPTION_CHARS],
        }
        for c in candidates
    ]
    prompt = load_prompt("reranking_prompt")
    # .replace, not .format — both the prompt and the payload contain JSON braces.
    prompt = prompt.replace("{genome}", json.dumps(genome.model_dump(), indent=2))
    prompt = prompt.replace("{candidates}", json.dumps(payload, indent=2))

    try:
        result = generate_structured(prompt, RerankResponse)
    except AIError as exc:
        # Keep the vector ordering rather than losing the candidates entirely,
        # but say so: a silent fallback looks like a working rerank that just
        # produced tightly-bunched scores and no reasons.
        log.warning("rerank failed, falling back to vector order: %s", exc)
        return sorted(candidates, key=lambda c: -c.confidence)

    judged = {r.id: r for r in result.candidates}
    out: List[ProblemCandidate] = []
    for candidate in candidates:
        verdict = judged.get(candidate.id)
        if verdict is None:
            # The model dropped this id. Keep it at its retrieval score rather
            # than silently losing a candidate the search thought was relevant.
            out.append(candidate)
            continue
        out.append(candidate.model_copy(update={
            "confidence": max(0.0, min(1.0, float(verdict.confidence))),
            "reason": verdict.reason.strip() or None,
        }))

    return sorted(out, key=_sort_key)
