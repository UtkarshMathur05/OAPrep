"""Extraction tests.

    .venv/Scripts/python.exe -m ai.tests.test_extraction

Offline tests run anywhere. The live tests need GEMINI_API_KEY and are skipped
without one. Plain asserts, no pytest — this is a 36-hour project.

The live tests exist for one reason: to catch the prompt drifting on hedged
detail routing. If "I think maybe X" starts landing in `constraints`, the
uncertainty story the whole demo rests on is broken (CLAUDE.md §19).
"""

from __future__ import annotations

import os
import sys

from ai.extraction.genome import extract_genome, normalize
from ai.models.problem_genome import ProblemGenome

# (transcript, must appear somewhere in uncertainties, must NOT appear in constraints)
HEDGED_CASES = [
    (
        "I remember a grid problem where you had to move right or down and find "
        "the minimum cost. I think there were some obstacles, but I am not sure.",
        "obstacle",
        "obstacle",
    ),
    (
        "There was an array and you had to find two numbers adding to a target. "
        "Maybe the array was sorted? I really can't remember.",
        "sort",
        "sort",
    ),
    (
        "Something with a linked list, reversing it I think. Possibly in groups "
        "of k, but that might be a different problem.",
        "k",
        "group",
    ),
    (
        "A tree problem, definitely binary. You return the maximum depth. I "
        "vaguely recall n being up to 10^5 but don't quote me.",
        "10^5",
        "10^5",
    ),
]

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        failures.append(name)


def test_offline() -> None:
    print("offline:")
    check("empty transcript returns empty genome", extract_genome("").is_empty())
    check("whitespace transcript returns empty genome", extract_genome("  \n ").is_empty())

    messy = ProblemGenome(
        concepts=["  Grid ", "GRID", "dynamic  programming"],
        objective="  Minimize   COST ",
        uncertainties=["Maybe obstacles", "Maybe obstacles"],
    )
    tidy = normalize(messy)
    check("concepts lowercased and deduped", tidy.concepts == ["grid", "dynamic programming"],
          str(tidy.concepts))
    check("objective normalized", tidy.objective == "minimize cost", repr(tidy.objective))
    check("uncertainties deduped", tidy.uncertainties == ["Maybe obstacles"],
          str(tidy.uncertainties))


def test_live() -> None:
    print("live (hedged detail routing):")
    for transcript, want_uncertain, avoid_in_constraints in HEDGED_CASES:
        genome = extract_genome(transcript)
        label = transcript[:42].rstrip() + "..."

        uncertainties = " ".join(genome.uncertainties).lower()
        constraints = " ".join(genome.constraints).lower()

        check(f"[{label}] hedge -> uncertainties ({want_uncertain!r})",
              want_uncertain.lower() in uncertainties,
              f"uncertainties={genome.uncertainties}")
        check(f"[{label}] hedge NOT in constraints ({avoid_in_constraints!r})",
              avoid_in_constraints.lower() not in constraints,
              f"constraints={genome.constraints}")
        check(f"[{label}] produced something searchable",
              not genome.is_empty(), "genome is empty")


def main() -> int:
    test_offline()
    if os.getenv("GEMINI_API_KEY"):
        test_live()
    else:
        print("live: SKIPPED (no GEMINI_API_KEY)")

    print()
    if failures:
        print(f"{len(failures)} failed")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
