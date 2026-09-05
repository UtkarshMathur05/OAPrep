"""Step 6 — Reconstruct a full problem statement from genome + best candidate.

Two things make this more than "print the stored description":

1. Provenance. Every section is labelled remembered / retrieved / inferred, and
   conflicts between the memory and the real problem land in `notes`. That
   distinction is the product (CLAUDE.md §19), and it is what Screen 4 renders.
2. stdin/stdout phrasing. Judge0 executes a script that reads stdin and prints
   stdout, so the statement has to describe the problem in those terms and the
   examples must be literal stdin/stdout text (CLAUDE.md §9).
"""

from __future__ import annotations

import json

from ai.gemini_client import AIError, generate_structured, load_prompt
from ai.models.problem_genome import (
    ProblemCandidate, ProblemGenome, ProblemProvenance, ReconstructedProblem)

# Enough of the real statement to reconstruct faithfully without a huge prompt.
_DESCRIPTION_CHARS = 2500


def _fallback(candidate: ProblemCandidate) -> ReconstructedProblem:
    """Show the retrieved problem verbatim when Gemini is unavailable.

    Everything is marked "retrieved" because that is exactly what it is: no
    reconstruction happened, and claiming otherwise would be the one thing this
    product must never do.
    """
    return ReconstructedProblem(
        title=candidate.title,
        description=candidate.description or "",
        confidence=candidate.confidence,
        provenance=ProblemProvenance(),
        notes=["Shown as stored: the problem could not be reconstructed just now."],
    )


def reconstruct_problem(
    genome: ProblemGenome, candidate: ProblemCandidate
) -> ReconstructedProblem:
    """Rebuild a full, self-contained problem statement."""
    payload = {
        "title": candidate.title,
        "difficulty": candidate.difficulty,
        "topics": candidate.topics,
        "source_url": candidate.source_url,
        "description": (candidate.description or "")[:_DESCRIPTION_CHARS],
    }

    prompt = load_prompt("reconstruction_prompt")
    # .replace, not .format — both the prompt and the payload contain JSON braces.
    prompt = prompt.replace("{genome}", json.dumps(genome.model_dump(), indent=2))
    prompt = prompt.replace("{candidate}", json.dumps(payload, indent=2))

    try:
        problem = generate_structured(prompt, ReconstructedProblem)
    except AIError:
        return _fallback(candidate)

    # Never let the reconstruction lose the candidate's identity.
    if not problem.title:
        problem = problem.model_copy(update={"title": candidate.title})
    if not problem.description:
        return _fallback(candidate)
    return problem
