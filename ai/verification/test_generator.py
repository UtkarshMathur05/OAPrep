"""Step 7 — Generate test cases for a reconstructed problem.

The hard part is not inventing inputs, it is the **format**. Judge0 runs a
script over stdin, so `input` must be the literal text the solution reads. Asked
without an exemplar the model happily returns `[[1,3,1],[1,5,1],[4,2,1]]`, a
JSON literal that no stdin parser will accept — every case then fails for
reasons that have nothing to do with the user's solution.

Two sources, in order of trust:

1. The reconstruction's own examples. Already stdin/stdout, already shown to the
   user, cost nothing. This is the primary path.
2. Cold generation, when a problem has no examples. The model is asked for a
   *reference solution* alongside the inputs, so the backend can execute it and
   keep only the cases where running the code agrees with the claimed answer.
   Asked for answers alone it produces inconsistent formats and wrong
   arithmetic — measured on two-sum, one case put the target first, another put
   it last, and a third was wrong under either reading.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from ai.gemini_client import AIError, generate_structured
from ai.models.problem_genome import ReconstructedProblem, TestCase

log = logging.getLogger(__name__)

MAX_CASES = 5
_DESCRIPTION_CHARS = 2500


class _GeneratedCases(BaseModel):
    cases: List[TestCase] = Field(default_factory=list)


class GeneratedSuite(BaseModel):
    """Candidate cases plus the code that is supposed to produce them."""

    reference_solution: str = ""
    cases: List[TestCase] = Field(default_factory=list)


_PROMPT = """Write a reference solution and {count} test cases for this problem.

The solution is run as a script: it reads ALL of stdin and prints to stdout.

reference_solution:
- Complete, runnable Python 3. No markdown fences, no commentary.
- It defines the stdin format. Parse whatever shape you choose consistently.
- Print only the answer.

cases:
- "input" is the exact text placed on stdin. Every case must use the SAME
  format your reference_solution parses. Do not vary the order or shape between
  cases.
- "expected_output" is exactly what your reference_solution prints for it.
- Never use JSON array syntax like [[1,2],[3,4]] unless your solution parses it.
- Include a smallest-possible case and at least one edge case.

Your solution will be executed against these inputs and any case whose real
output differs from "expected_output" will be discarded, so make them agree.

{format_hint}

TITLE: {title}

PROBLEM:
{description}
"""

_FORMAT_FROM_EXAMPLES = """The stdin format is already fixed by these examples.
Your reference_solution must parse exactly this shape:

{examples}
"""

_FORMAT_UNKNOWN = """No example is available. Choose the simplest plausible
whitespace-separated format — sizes first, then values — and stay consistent.
"""


def _clean(cases: List[TestCase]) -> List[TestCase]:
    """Drop blanks and duplicate inputs; trailing whitespace is stripped at
    compare time anyway, so normalise it here too."""
    seen: set[str] = set()
    out: List[TestCase] = []
    for c in cases:
        stdin = (c.input or "").rstrip()
        expected = (c.expected_output or "").rstrip()
        if not stdin or not expected or stdin in seen:
            continue
        seen.add(stdin)
        out.append(TestCase(input=stdin, expected_output=expected,
                            explanation=c.explanation))
    return out


def _format_hint(problem: ReconstructedProblem) -> str:
    if not problem.examples:
        return _FORMAT_UNKNOWN
    shown = "\n\n".join(
        f"input:\n{e.input}\noutput:\n{e.output}" for e in problem.examples[:2]
    )
    return _FORMAT_FROM_EXAMPLES.format(examples=shown)


def cases_from_examples(problem: ReconstructedProblem) -> List[TestCase]:
    """Primary source: reuse the reconstruction's own examples.

    Costs nothing and needs no validation — the model already committed to
    these, and they are the pairs the user is being shown on screen.
    """
    return _clean([
        TestCase(input=e.input, expected_output=e.output, explanation=e.explanation)
        for e in problem.examples
    ])


def generate_suite(problem: ReconstructedProblem, count: int = MAX_CASES) -> GeneratedSuite:
    """Fallback source: ask for cases *and* the code that produces them.

    The caller is expected to run `reference_solution` against each input and
    drop the cases that disagree — see backend/app/api/verify.py. Never raises;
    an empty suite means "no tests", which is a state the UI reports.
    """
    prompt = _PROMPT.format(
        count=count,
        format_hint=_format_hint(problem),
        title=problem.title,
        description=(problem.description or "")[:_DESCRIPTION_CHARS],
    )
    try:
        suite = generate_structured(prompt, GeneratedSuite)
    except AIError as exc:
        log.warning("test generation failed for %r: %s", problem.title, exc)
        return GeneratedSuite()

    return GeneratedSuite(
        reference_solution=_strip_fences(suite.reference_solution),
        cases=_clean(suite.cases)[:count],
    )


def _strip_fences(code: str) -> str:
    """Models add ```python fences even when told not to."""
    text = (code or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text.strip()
