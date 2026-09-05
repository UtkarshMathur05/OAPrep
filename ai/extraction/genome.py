"""Step 1 — Memory extraction: transcript -> ProblemGenome.

The one job that matters here is keeping hedged details out of `constraints` and
in `uncertainties`. Everything downstream trusts that distinction, and the demo
is built on showing it (CLAUDE.md §19).
"""

from __future__ import annotations

from typing import List

from ai import gemini_client
from ai.models.problem_genome import ProblemGenome

# Long transcripts are rambling, not informative, and they cost latency.
MAX_TRANSCRIPT_CHARS = 8000
# Guard against a model that pads a field into uselessness.
MAX_ITEMS = 12

# Per the prompt, these are lowercase vocabulary fields. `uncertainties` and
# `constraints` are short clauses and keep whatever case the model chose.
_LOWERCASE_FIELDS = ("concepts", "operations", "data_structures", "algorithm_hints")


def _clean(items: List[str], *, lowercase: bool) -> List[str]:
    """Strip, optionally lowercase, drop blanks, dedupe preserving order."""
    seen: set[str] = set()
    out: List[str] = []
    for item in items or []:
        text = " ".join(str(item).split())
        if lowercase:
            text = text.lower()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out[:MAX_ITEMS]


def normalize(genome: ProblemGenome) -> ProblemGenome:
    """Tidy a raw model response. Pure function — testable without an API key."""
    data = genome.model_dump()
    for field in _LOWERCASE_FIELDS:
        data[field] = _clean(data.get(field, []), lowercase=True)
    for field in ("constraints", "uncertainties"):
        data[field] = _clean(data.get(field, []), lowercase=False)

    objective = data.get("objective")
    objective = " ".join(str(objective).split()).lower() if objective else None
    data["objective"] = objective or None

    return ProblemGenome(**data)


def extract_genome(transcript: str) -> ProblemGenome:
    """Turn a vague spoken/typed memory into a structured genome.

    Returns an empty genome for empty input rather than calling the API — an
    empty memory is a user error, not a reason to spend quota or fail.
    """
    text = " ".join((transcript or "").split())
    if not text:
        return ProblemGenome()

    prompt = gemini_client.load_prompt("extraction_prompt")
    # .replace, not .format — the prompt contains literal JSON braces that
    # str.format would choke on.
    prompt = prompt.replace("{transcript}", text[:MAX_TRANSCRIPT_CHARS])

    return normalize(gemini_client.generate_structured(prompt, ProblemGenome))
