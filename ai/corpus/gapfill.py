"""Corpus step 3 — describe the premium-locked problems with Gemini.

fetch_descriptions.py records source="locked" (or "error") for problems whose
statement LeetCode would not serve. This fills those in, appending to
descriptions.jsonl with source="gemini". Resumable.

    python -m ai.corpus.gapfill

Requires GEMINI_API_KEY. Expect roughly 10-20% of the corpus to need this.

The model is asked for topics as well as text: load_corpus embeds title and
topics FIRST, so a row without topics retrieves measurably worse than one with.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from ai.gemini_client import AIError, generate_structured, is_daily_quota

OUT_DIR = Path(__file__).parent / "out"
INDEX = OUT_DIR / "index.jsonl"
DEST = OUT_DIR / "descriptions.jsonl"

# Not algorithm problems, so they cannot be verified through Python on Judge0
# (CLAUDE.md §9). They would only ever be dead ends in the demo.
SKIP_SLUGS = {
    "number-of-transactions-per-visit",  # SQL
    "viewers-turned-streamers",          # SQL
    "convert-json-string-to-object",     # JavaScript
    "web-crawler-multithreaded",         # concurrency
}

PROMPT = """You are recalling a specific LeetCode problem: "{title}"
(difficulty: {difficulty}, slug: {slug}).

Set recognized=true ONLY if you genuinely know this exact problem. If the title
is merely plausible, or you would be guessing at the task, set recognized=false
and leave the other fields empty. A wrong problem statement is far worse than a
missing one: it silently corrupts search results for everyone using this corpus.

When recognized=true:
- description: the task, the input/output, and typical constraints. Plain text,
  no markdown headers, under 200 words. Do not invent a different problem.
- topics: LeetCode topic tags, e.g. ["Array", "Hash Table"], Title Case."""


class GapfillResult(BaseModel):
    """Structured reply so 'I do not know' is a field, not a magic string."""

    recognized: bool = False
    description: str = ""
    topics: List[str] = Field(default_factory=list)


def load_records() -> list[dict]:
    if not DEST.exists():
        return []
    return [json.loads(l) for l in DEST.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    index = {json.loads(l)["slug"]: json.loads(l)
             for l in INDEX.read_text(encoding="utf-8").splitlines() if l.strip()}
    records = load_records()

    # Keep the last record per slug, then find the ones still missing text.
    latest = {r["slug"]: r for r in records}
    todo = [s for s, r in latest.items() if not r.get("description")]

    skipped_kind = [s for s in todo if s in SKIP_SLUGS]
    todo = [s for s in todo if s not in SKIP_SLUGS]
    for slug in skipped_kind:
        print(f"  skipping {slug} (not a Python algorithm problem)")

    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(todo)} problems need a Gemini description")
    filled = unknown = failed = 0

    with DEST.open("a", encoding="utf-8") as out:
        for i, slug in enumerate(todo, 1):
            meta = index.get(slug, {})
            title = meta.get("title", slug)
            try:
                result = generate_structured(
                    PROMPT.format(title=title,
                                  difficulty=meta.get("difficulty", "unknown"),
                                  slug=slug),
                    GapfillResult,
                )
            except AIError as exc:  # one bad row must not kill the run
                if is_daily_quota(exc):
                    print(f"  [{i}/{len(todo)}] daily quota exhausted - stopping.")
                    print("  Re-run tomorrow, or set GEMINI_TEXT_MODEL to another "
                          "model (each has its own daily bucket).")
                    break
                print(f"  [{i}/{len(todo)}] FAIL {title}: {str(exc)[:80]}")
                failed += 1
                continue

            if not result.recognized or not result.description.strip():
                # Better an honest gap than a hallucinated problem in the corpus.
                print(f"  [{i}/{len(todo)}] unknown to Gemini: {title}")
                unknown += 1
                continue

            out.write(json.dumps({
                "slug": slug,
                "description": result.description.strip(),
                "topics": result.topics,
                "source": "gemini",
            }) + "\n")
            out.flush()
            filled += 1
            if i % 25 == 0:
                print(f"  [{i}/{len(todo)}] filled={filled} unknown={unknown} failed={failed}")

    print(f"done: {filled} described, {unknown} unknown, {failed} errored")
    print(f"      {len(skipped_kind)} skipped as non-algorithm")


if __name__ == "__main__":
    main()
