"""Corpus step 3 — describe the premium-locked problems with Gemini.

fetch_descriptions.py records source="locked" (or "error") for problems whose
statement LeetCode would not serve. This fills those in, appending to
descriptions.jsonl with source="gemini". Resumable.

    python -m ai.corpus.gapfill

Requires GEMINI_API_KEY. Expect roughly 10-20% of the corpus to need this.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai.gemini_client import generate_text

OUT_DIR = Path(__file__).parent / "out"
INDEX = OUT_DIR / "index.jsonl"
DEST = OUT_DIR / "descriptions.jsonl"

PROMPT = """Write the problem statement for the LeetCode problem "{title}"
(difficulty: {difficulty}, slug: {slug}).

Write only what you are confident is part of this specific problem. Include the
task, the input/output description, and typical constraints. Do not invent a
different problem. If you do not recognise the problem, reply with exactly:
UNKNOWN

Plain text, no markdown headers, under 200 words."""


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
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(todo)} problems need a Gemini description")
    filled = skipped = 0

    with DEST.open("a", encoding="utf-8") as out:
        for i, slug in enumerate(todo, 1):
            meta = index.get(slug, {})
            try:
                text = generate_text(PROMPT.format(
                    title=meta.get("title", slug),
                    difficulty=meta.get("difficulty", "unknown"),
                    slug=slug,
                ))
            except Exception as exc:  # noqa: BLE001 - one bad row must not kill the run
                print(f"  [{i}/{len(todo)}] FAIL {slug}: {exc}")
                skipped += 1
                continue

            if not text or text.strip().upper().startswith("UNKNOWN"):
                # Better an honest gap than a hallucinated problem in the corpus.
                print(f"  [{i}/{len(todo)}] unknown to Gemini: {slug}")
                skipped += 1
                continue

            out.write(json.dumps({"slug": slug, "description": text,
                                  "topics": [], "source": "gemini"}) + "\n")
            out.flush()
            filled += 1
            if i % 25 == 0:
                print(f"  [{i}/{len(todo)}] filled={filled} skipped={skipped}")

    print(f"done: {filled} described, {skipped} left without text")


if __name__ == "__main__":
    main()
