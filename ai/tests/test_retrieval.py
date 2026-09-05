"""Retrieval quality harness.

    .venv/Scripts/python.exe -m ai.tests.test_retrieval            # recall@k, no text quota
    .venv/Scripts/python.exe -m ai.tests.test_retrieval --rerank   # also measure reranked recall@1

Genomes are hand-written rather than extracted, on purpose:
  * it isolates retrieval quality from extraction quality, so a regression
    points at one module;
  * extraction costs a text request per case, and the free tier allows 20 a day.

Embeddings are cached after the first run, so repeats are free and offline.
"""

from __future__ import annotations

import argparse
import sys

from ai.models.problem_genome import ProblemGenome
from ai.retrieval.vector_search import search_candidates

# (label, genome fields, expected slug) — what a vague memory of each looks like.
CASES = [
    ("grid, right/down, cheapest path",
     dict(concepts=["grid", "dynamic programming"], operations=["move right", "move down"],
          objective="minimize cost", data_structures=["2d array"]),
     "minimum-path-sum"),
    ("two numbers adding to a target",
     dict(concepts=["array"], objective="find two numbers that sum to a target",
          data_structures=["hash map"]),
     "two-sum"),
    ("cache that evicts least recently used",
     dict(concepts=["cache", "design"], operations=["get", "put"],
          objective="evict least recently used", data_structures=["hash map", "linked list"]),
     "lru-cache"),
    ("brackets balanced correctly",
     dict(concepts=["string"], objective="check brackets are balanced",
          data_structures=["stack"]),
     "valid-parentheses"),
    ("combine overlapping intervals",
     dict(concepts=["intervals", "sorting"], operations=["merge"],
          objective="merge overlapping intervals"),
     "merge-intervals"),
    ("longest stretch with no repeated character",
     dict(concepts=["string"], objective="longest substring without repeating characters",
          algorithm_hints=["sliding window"]),
     "longest-substring-without-repeating-characters"),
    ("count islands in a grid of land and water",
     dict(concepts=["grid", "graph"], objective="count connected land regions",
          algorithm_hints=["dfs", "bfs"]),
     "number-of-islands"),
    ("best day to buy and sell a stock once",
     dict(concepts=["array"], objective="maximise profit from one buy and one sell"),
     "best-time-to-buy-and-sell-stock"),
    ("reverse a linked list",
     dict(concepts=["linked list"], operations=["reverse"], objective="reverse the list"),
     "reverse-linked-list"),
    ("print a tree level by level",
     dict(concepts=["binary tree"], objective="traverse level by level",
          algorithm_hints=["bfs"], data_structures=["queue"]),
     "binary-tree-level-order-traversal"),
]

# Deliberately underspecified: what someone actually says when they only half
# remember. Sparse, missing the giveaway keyword, or carrying a wrong detail.
# CASES is the floor; these are the honest measure.
VAGUE_CASES = [
    ("just 'grid' and 'count the ways'",
     dict(concepts=["grid"], objective="count the number of ways to reach the end"),
     "unique-paths"),
    ("something about a palindrome in a string",
     dict(concepts=["string"], objective="find the longest palindrome"),
     "longest-palindromic-substring"),
    ("k largest, can't recall the structure",
     dict(concepts=["array"], objective="find the kth largest element"),
     "kth-largest-element-in-an-array"),
    ("two sorted lists into one",
     dict(concepts=["linked list"], objective="combine two sorted lists"),
     "merge-two-sorted-lists"),
    ("rooms and meetings, no other detail",
     dict(concepts=["intervals"], objective="how many rooms are needed"),
     "meeting-rooms-ii"),
    ("climbing something, counting ways",
     dict(concepts=["dynamic programming"], objective="count ways to climb"),
     "climbing-stairs"),
]

TOP_K = 10


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rerank", action="store_true",
                    help="also measure recall@1 after LLM reranking (1 request per case)")
    args = ap.parse_args()

    from ai.retrieval.reranker import rerank as rerank_fn

    all_cases = [("clear", c) for c in CASES] + [("vague", c) for c in VAGUE_CASES]
    hits = {1: 0, 3: 0, 5: 0, 10: 0}
    vague_hits = {1: 0, 5: 0}
    reranked_hits = 0
    missed = []

    for tier, (label, fields, expected) in all_cases:
        genome = ProblemGenome(**fields)
        candidates = search_candidates(genome, top_k=TOP_K)
        slugs = [c.slug for c in candidates]
        position = slugs.index(expected) + 1 if expected in slugs else None

        for k in hits:
            if position and position <= k:
                hits[k] += 1
        if tier == "vague":
            for k in vague_hits:
                if position and position <= k:
                    vague_hits[k] += 1

        mark = f"#{position}" if position else "MISS"
        line = f"  [{tier:>5}] {mark:>5}  {label}"

        if args.rerank:
            ranked = rerank_fn(genome, candidates)
            top = ranked[0].slug if ranked else None
            ok = top == expected
            reranked_hits += ok
            line += f"   | reranked #1: {'HIT' if ok else top}"

        print(line)
        if not position:
            missed.append((label, expected, slugs[:3]))

    n = len(all_cases)
    nv = len(VAGUE_CASES)
    print()
    for k in sorted(hits):
        print(f"  recall@{k:<2} {hits[k]}/{n}  ({hits[k]/n*100:.0f}%)")
    print(f"  vague-only recall@1 {vague_hits[1]}/{nv}  "
          f"recall@5 {vague_hits[5]}/{nv}")
    if args.rerank:
        print(f"  reranked recall@1  {reranked_hits}/{n}  ({reranked_hits/n*100:.0f}%)")

    if missed:
        print("\nmissed entirely:")
        for label, expected, got in missed:
            print(f"  {label}\n    wanted {expected}\n    got    {got}")

    # The vague tier is the real bar: recall@5 is what the UI shows.
    return 0 if vague_hits[5] == nv else 1


if __name__ == "__main__":
    sys.exit(main())
