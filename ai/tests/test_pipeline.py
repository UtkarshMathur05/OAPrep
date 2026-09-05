"""Golden demo path, end to end, with no server involved.

    .venv/Scripts/python.exe -m ai.tests.test_pipeline

memory -> genome -> candidates -> reranked -> reconstructed problem.

This is the run to do before demoing: it warms the cache for every stage, so the
live demo is instant and survives bad wifi (CLAUDE.md §28). Needs Postgres up
and GEMINI_API_KEY set; costs ~3 text requests cold, 0 warm.
"""

from __future__ import annotations

import sys

GOLDEN = ("I remember a grid problem where you had to move right or down and find "
          "the minimum cost. I think there were some obstacles, but I am not sure.")
EXPECTED_SLUG = "minimum-path-sum"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   {detail}" if not ok else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    from ai.extraction.genome import extract_genome
    from ai.reconstruction.reconstruct import reconstruct_problem
    from ai.retrieval.reranker import rerank
    from ai.retrieval.vector_search import search_candidates

    print("1. extraction")
    genome = extract_genome(GOLDEN)
    print(f"     {genome.to_query_text()}")
    check("genome is searchable", not genome.is_empty())
    check("hedged detail became an uncertainty",
          any("obstacle" in u.lower() for u in genome.uncertainties),
          str(genome.uncertainties))
    check("nothing hedged leaked into constraints",
          not any("obstacle" in c.lower() for c in genome.constraints),
          str(genome.constraints))

    print("2. retrieval")
    candidates = search_candidates(genome, top_k=8)
    check("returned candidates", bool(candidates))
    check(f"{EXPECTED_SLUG} in top 8",
          EXPECTED_SLUG in [c.slug for c in candidates],
          str([c.slug for c in candidates][:4]))

    print("3. reranking")
    ranked = rerank(genome, candidates)
    top = ranked[0] if ranked else None
    print(f"     top: {top.slug} @ {top.confidence:.2f}" if top else "     none")
    check(f"{EXPECTED_SLUG} ranked first", bool(top) and top.slug == EXPECTED_SLUG,
          top.slug if top else "no candidates")
    check("confidences actually spread",
          len(ranked) < 2 or (ranked[0].confidence - ranked[-1].confidence) > 0.15,
          "reranking may have degraded to retrieval order")

    print("4. reconstruction")
    problem = reconstruct_problem(genome, ranked[0])
    print(f"     {problem.title}  (confidence {problem.confidence:.2f})")
    check("has a description", len(problem.description) > 80)
    check("examples are stdin/stdout, not function-call shorthand",
          bool(problem.examples) and all(
              "=" not in e.input.split("\n")[0] for e in problem.examples),
          str([e.input[:30] for e in problem.examples]))
    check("provenance is not all 'remembered'",
          problem.provenance.description != "remembered"
          or problem.provenance.constraints != "remembered")
    check("noted the obstacles conflict",
          any("obstacle" in n.lower() for n in problem.notes),
          str(problem.notes))
    check("plain text, no LaTeX", "\times" not in problem.description
          and "$" not in problem.description)

    print()
    if failures:
        print(f"{len(failures)} failed")
        return 1
    print("golden path OK - cache is warm, demo will run offline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
