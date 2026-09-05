"""Step 6 — Reconstruct a full problem statement from genome + best candidate.

TODO(ai): call Gemini with prompts/reconstruction_prompt.txt.
"""

from ai.models.problem_genome import ProblemCandidate, ProblemGenome, ReconstructedProblem


def reconstruct_problem(genome: ProblemGenome, candidate: ProblemCandidate) -> ReconstructedProblem:
    raise NotImplementedError
