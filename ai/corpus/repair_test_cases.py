"""Repair test cases whose stdin formats disagree.

The bug this exists for: `save_test_cases` used to merge on `input` alone, so
every reconstruction of a problem appended its own examples. Two-sum collected
nine cases across three incompatible shapes and capped at 4/9 for a correct
solution. The merge is fixed; this cleans up what it already stored.

Execution is the arbiter, not a heuristic. A structural signature cannot do it:
minimum-path-sum's cases legitimately have different line counts (the grid is
part of the input) while two-sum's differ for the worst reason. The question
"do these cases share one format" only has a real answer as "does one program
pass them all", so we ask for a reference solution and run it on Judge0.

    python -m ai.corpus.repair_test_cases            # report only
    python -m ai.corpus.repair_test_cases --apply    # delete the losers

Never deletes a problem's last case: a problem with no tests is worse than a
problem with one, and a Judge0 outage must not look like a format disagreement.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from pydantic import BaseModel

from ai.gemini_client import AIError, generate_structured

sys.path.insert(0, "backend")

log = logging.getLogger("repair")


class _Reference(BaseModel):
    """The format the majority of stored inputs are written in, plus a solver."""

    io_format: str = ""
    reference_solution: str = ""


_PROMPT = """These test case inputs were collected for one problem over time and
some of them are written in DIFFERENT stdin formats. Your job is to decide which
single format is correct and write a program that reads it.

Choose the format that the LARGEST NUMBER of the inputs below are written in. Do
not invent a new format, and do not try to accept several formats at once — a
solution that guesses per-input is exactly what we are removing.

io_format:
- One line per line of stdin, then a final line starting "Output:". The output
  line is required — printing "[0, 1]" where the cases say "0 1" fails
  everything, so the expected shape has to be stated, not left implied.
- Be unambiguous about order: "an array and a target" does not say which comes
  first.

reference_solution:
- Complete runnable Python 3, no markdown fences, no commentary.
- Real newlines and real indentation. Do NOT collapse it onto one line with
  semicolons: `a; for x in y: b` is a syntax error and the whole audit is then
  worthless.
- Reads stdin, parses exactly your io_format, prints only the answer.
- It will be executed against every input below. Inputs written in a different
  format are expected to crash or print the wrong answer; that is the point.
- Match the OUTPUT shape of the stored cases exactly too — printing "[0, 1]"
  where they say "0 1" fails every case and tells us nothing about the input
  formats, which is the only thing we are trying to measure.
- Compute the answer. Do not map the inputs below to their answers: a lookup
  table passes every case regardless of format and defeats the entire audit.

TITLE: {title}

PROBLEM:
{description}

STORED CASES (stdin, then the expected stdout, one pair per ---):
{cases}
"""


def _looks_hardcoded(code: str, cases: List[dict]) -> bool:
    """A lookup table passes every case whatever its format, so it would report
    a corrupt suite as clean. Crude but cheap: the expected answers should not
    appear verbatim as string literals in a program that computes them."""
    quoted = sum(f'"{c["expected_output"]}"' in code or f"\'{c['expected_output']}\'" in code
                 for c in cases)
    return quoted >= max(2, len(cases) // 2)


def _fences(code: str) -> str:
    text = (code or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text.strip()


class Audit(BaseModel):
    """What one problem's audit concluded.

    `conclusive` matters more than it looks: a broken reference and a clean
    suite both leave every case in `kept`, and reporting the second when it was
    the first is how you tell someone their corrupt data is fine.
    """

    io_format: str = ""
    kept: list = []
    dropped: list = []
    conclusive: bool = False
    note: str = ""


def audit(problem: dict, cases: List[dict], attempts: int = 2) -> Audit:
    """Decide which of a problem's cases share one format.

    Inconclusive on any failure — no API key, Judge0 down, reference does not
    compile or agrees with nothing — and inconclusive keeps every case. This
    script deletes rows, so absence of evidence must never read as evidence.
    """
    from app.services import judge_service

    shown = "\n---\n".join(
        f"stdin:\n{c['input']}\nstdout:\n{c['expected_output']}" for c in cases
    )
    prompt = _PROMPT.format(title=problem["title"],
                            description=(problem["description"] or "")[:2000],
                            cases=shown)
    inconclusive = lambda why: Audit(kept=cases, note=why)  # noqa: E731

    ref = None
    for attempt in range(attempts):
        try:
            candidate = generate_structured(prompt, _Reference)
        except AIError as exc:
            return inconclusive(f"no reference ({exc})")
        code = _fences(candidate.reference_solution)
        # Compile locally first: a syntax error costs nothing to catch here and
        # a whole Judge0 batch to discover, where it looks identical to every
        # case being in the wrong format.
        try:
            compile(code, "<reference>", "exec")
        except SyntaxError as exc:
            log.info("%s: reference did not compile (%s), retry %d",
                     problem["slug"], exc.msg, attempt + 1)
            continue
        if _looks_hardcoded(code, cases):
            log.info("%s: reference hard-codes the answers, retry %d",
                     problem["slug"], attempt + 1)
            continue
        ref, ref_code = candidate, code
        break
    if ref is None:
        return inconclusive("no reference compiled")

    actual = judge_service.run_reference(ref_code, [c["input"] for c in cases])
    if all(a is None for a in actual):
        # Judge0 down, or the reference crashes on everything. Either way we
        # have learned nothing about the formats.
        return inconclusive("reference produced no output on any case")

    kept, dropped = [], []
    for case, got in zip(cases, actual):
        agree = got is not None and got.rstrip() == case["expected_output"].rstrip()
        (kept if agree else dropped).append(case)

    if not kept:
        return inconclusive("reference agreed with no stored case")

    from ai.verification.test_generator import ensure_output_line

    return Audit(
        io_format=ensure_output_line(
            ref.io_format, [c["expected_output"] for c in kept]),
        kept=kept, dropped=dropped, conclusive=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="delete disagreeing cases and store the format")
    parser.add_argument("--slug", help="repair one problem instead of all")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from app.services import database_service as db

    rows = db.query(
        """
        SELECT p.slug, p.title, p.description, count(t.id) AS cases
        FROM problems p JOIN test_cases t ON t.problem_id = p.id
        WHERE (%(slug)s::text IS NULL OR p.slug = %(slug)s::text)
        GROUP BY p.slug, p.title, p.description
        HAVING count(t.id) > 1
        ORDER BY count(t.id) DESC
        """,
        {"slug": args.slug},
    )

    total_dropped = inconclusive = 0
    for problem in rows:
        cases = db.query(
            """
            SELECT t.id::text AS id, t.input, t.expected_output
            FROM test_cases t JOIN problems p ON p.id = t.problem_id
            WHERE p.slug = %s ORDER BY t.created_at
            """,
            (problem["slug"],),
        )
        result = audit(problem, cases)
        if not result.conclusive:
            inconclusive += 1
            print(f"{problem['slug']:<40} {len(cases):>2} cases  ?? {result.note}")
            continue

        status = "consistent" if not result.dropped else f"DROP {len(result.dropped)}/{len(cases)}"
        print(f"{problem['slug']:<40} {len(result.kept):>2} kept    {status}")
        for case in result.dropped:
            print(f"    - {case['input']!r} -> {case['expected_output']!r}")

        if args.apply:
            if result.dropped:
                db.execute(
                    "DELETE FROM test_cases WHERE id = ANY(%s::uuid[])",
                    ([c["id"] for c in result.dropped],),
                )
            if result.io_format:
                db.execute(
                    "UPDATE problems SET io_format = %s WHERE slug = %s",
                    (result.io_format, problem["slug"]),
                )
        total_dropped += len(result.dropped)

    verb = "deleted" if args.apply else "would be deleted"
    print(f"\n{len(rows)} problems, {total_dropped} cases {verb}, "
          f"{inconclusive} inconclusive (left untouched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
