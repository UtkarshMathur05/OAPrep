"""Step 7 — Generate test cases for a reconstructed problem.

TODO(ai): prompt Gemini for input/expected_output pairs in stdin/stdout form so
they can be handed straight to Judge0.
"""

from typing import List

from ai.models.problem_genome import ReconstructedProblem, TestCase


def generate_test_cases(problem: ReconstructedProblem, count: int = 5) -> List[TestCase]:
    raise NotImplementedError
