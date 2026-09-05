"""Step 5 — LLM reranking of retrieved candidates.

TODO(ai): call Gemini with prompts/reranking_prompt.txt, merge the returned
confidences/reasons back onto the candidates and sort.
"""

from typing import List

from ai.models.problem_genome import ProblemCandidate, ProblemGenome


def rerank(genome: ProblemGenome, candidates: List[ProblemCandidate]) -> List[ProblemCandidate]:
    raise NotImplementedError
