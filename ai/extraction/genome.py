"""Step 1 — Memory extraction: transcript -> ProblemGenome.

TODO(ai): call Gemini with prompts/extraction_prompt.txt and parse the JSON
into a ProblemGenome.
"""

from ai.models.problem_genome import ProblemGenome


def extract_genome(transcript: str) -> ProblemGenome:
    raise NotImplementedError
