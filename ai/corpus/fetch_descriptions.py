"""Corpus step 2 — fetch real problem statements from LeetCode's public GraphQL.

Reads out/index.jsonl, writes out/descriptions.jsonl. Resumable: rows already
present in the output are skipped, so you can Ctrl-C and re-run freely.

Premium-locked problems (isPaidOnly) return no content; they are recorded with
source="locked" for ai.corpus.gapfill to describe with Gemini.

    python -m ai.corpus.fetch_descriptions            # all of index.jsonl
    python -m ai.corpus.fetch_descriptions --limit 3  # smoke test

Uses only the stdlib so it runs before any venv exists.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path

OUT_DIR = Path(__file__).parent / "out"
INDEX = OUT_DIR / "index.jsonl"
DEST = OUT_DIR / "descriptions.jsonl"

GRAPHQL_URL = "https://leetcode.com/graphql"
QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    isPaidOnly
    topicTags { name }
  }
}
"""
HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0 (compatible; memoize-hackathon/0.1)",
}


def html_to_text(html: str) -> str:
    """Flatten LeetCode's HTML statement into embeddable plain text."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?i)<(br|/p|/div|/li|/pre)[^>]*>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "- ", text)
    # Exponents before the generic tag strip, else 10<sup>4</sup> -> "10 4".
    text = re.sub(r"(?is)<sup>\s*(.*?)\s*</sup>", r"^\1", text)
    text = re.sub(r"(?is)<sub>\s*(.*?)\s*</sub>", r"_\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def fetch(slug: str, timeout: float = 20.0) -> dict:
    payload = json.dumps({"query": QUERY, "variables": {"titleSlug": slug}}).encode()
    req = urllib.request.Request(GRAPHQL_URL, data=payload, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.load(resp)
    question = (body.get("data") or {}).get("question")
    if not question:
        raise LookupError(f"no question payload for {slug}")
    return question


def load_done() -> set[str]:
    if not DEST.exists():
        return set()
    done = set()
    with DEST.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                done.add(json.loads(line)["slug"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="stop after N new fetches")
    ap.add_argument("--delay", type=float, default=1.2, help="seconds between requests")
    args = ap.parse_args()

    rows = [json.loads(l) for l in INDEX.read_text(encoding="utf-8").splitlines() if l.strip()]
    done = load_done()
    todo = [r for r in rows if r["slug"] not in done]
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(done)} already fetched, {len(todo)} to go")
    ok = locked = failed = 0

    with DEST.open("a", encoding="utf-8") as out:
        for i, row in enumerate(todo, 1):
            slug = row["slug"]
            try:
                q = fetch(slug)
            except (urllib.error.URLError, LookupError, TimeoutError, json.JSONDecodeError) as exc:
                # Record the miss so gapfill picks it up; don't lose the whole run.
                print(f"  [{i}/{len(todo)}] FAIL {slug}: {exc}")
                out.write(json.dumps({"slug": slug, "description": None,
                                      "topics": [], "source": "error"}) + "\n")
                out.flush()
                failed += 1
                time.sleep(args.delay * 2)
                continue

            content = q.get("content")
            if q.get("isPaidOnly") or not content:
                record = {"slug": slug, "description": None, "topics": [], "source": "locked"}
                locked += 1
            else:
                record = {
                    "slug": slug,
                    "description": html_to_text(content),
                    "topics": [t["name"] for t in (q.get("topicTags") or [])],
                    "source": "leetcode",
                }
                ok += 1

            out.write(json.dumps(record) + "\n")
            out.flush()
            if i % 50 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] ok={ok} locked={locked} failed={failed}")
            # Jitter so we don't look like a metronome to their rate limiter.
            time.sleep(args.delay + random.uniform(0, 0.4))

    print(f"done: {ok} fetched, {locked} premium-locked, {failed} errored -> {DEST.name}")


if __name__ == "__main__":
    main()
