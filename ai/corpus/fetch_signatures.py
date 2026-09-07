"""Corpus step 5 — fetch typed signatures so problems can be solved as functions.

The statements were always written for a function signature: "given an array
nums and an integer target" says nothing about which line the target is on,
because upstream there are no lines. Running them over stdin meant every problem
told the reader one thing and the runner another.

The same GraphQL endpoint that gave us the statements also gives the signature,
so none of this is invented:

    metaData            {"name": "twoSum",
                         "params": [{"name": "nums", "type": "integer[]"},
                                    {"name": "target", "type": "integer"}],
                         "return": {"type": "integer[]"}}
    exampleTestcaseList ['[2,7,11,15]\\n9', '[3,2,4]\\n6', '[3,3]\\n6']
    codeSnippets        starter code, per language, already matching the signature

Note what is NOT here: expected outputs. LeetCode does not expose them, and
inventing them would be the confident fabrication the corpus rules out. They are
recovered in ai.corpus.load_signatures from the "Output:" lines of the
statement we already stored, and then confirmed by execution.

Reads slugs from Postgres (only problems we actually hold), writes
out/signatures.jsonl. Resumable: rows already in the output are skipped.

    python -m ai.corpus.fetch_signatures --limit 5   # smoke test
    python -m ai.corpus.fetch_signatures             # everything with a statement
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, "backend")

OUT_DIR = Path(__file__).parent / "out"
DEST = OUT_DIR / "signatures.jsonl"

GRAPHQL_URL = "https://leetcode.com/graphql"
QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    titleSlug
    metaData
    exampleTestcaseList
    codeSnippets { langSlug code }
  }
}
"""
HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0 (compatible; memoize/0.1)",
}

# Only the languages we can actually run. Storing the other eight snippets would
# triple the JSONB for nothing.
WANTED_LANGS = {
    "python3", "cpp", "java", "javascript", "c", "golang",
    "csharp", "kotlin", "ruby", "rust", "typescript",
}


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
    for line in DEST.read_text(encoding="utf-8").splitlines():
        try:
            done.add(json.loads(line)["slug"])
        except (json.JSONDecodeError, KeyError):
            continue
    return done


def _slugs(limit: int, only: str | None) -> list[str]:
    from app.services import database_service as db

    rows = db.query(
        """
        SELECT slug FROM problems
        WHERE coalesce(description, '') <> ''
          AND origin = 'corpus'
          AND (%(only)s::text IS NULL OR slug = %(only)s::text)
        ORDER BY popularity DESC NULLS LAST
        """,
        {"only": only},
    )
    return [r["slug"] for r in rows][: limit or None]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="stop after N new fetches")
    ap.add_argument("--slug", help="fetch one problem")
    ap.add_argument("--delay", type=float, default=1.2, help="seconds between requests")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    done = load_done()
    todo = [s for s in _slugs(args.limit, args.slug) if s not in done]
    print(f"{len(done)} already fetched, {len(todo)} to go")

    ok = nometa = failed = 0
    with DEST.open("a", encoding="utf-8") as out:
        for i, slug in enumerate(todo, 1):
            try:
                q = fetch(slug)
            except (urllib.error.URLError, LookupError, TimeoutError,
                    json.JSONDecodeError) as exc:
                print(f"  [{i}/{len(todo)}] FAIL {slug}: {exc}")
                failed += 1
                time.sleep(args.delay * 2)
                continue

            meta = q.get("metaData")
            try:
                signature = json.loads(meta) if meta else None
            except json.JSONDecodeError:
                signature = None

            # A problem with no parsable signature stays on stdin. Recording the
            # miss is the point: it is not a failure, it is a mode.
            if not signature or not signature.get("name"):
                nometa += 1
            else:
                ok += 1

            out.write(json.dumps({
                "slug": slug,
                "signature": signature,
                "example_inputs": q.get("exampleTestcaseList") or [],
                "code_snippets": {
                    c["langSlug"]: c["code"] for c in (q.get("codeSnippets") or [])
                    if c.get("langSlug") in WANTED_LANGS and c.get("code")
                },
            }) + "\n")
            out.flush()
            if i % 25 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] ok={ok} no-signature={nometa} failed={failed}")
            time.sleep(args.delay + random.uniform(0, 0.4))

    print(f"done: {ok} with signatures, {nometa} without, {failed} errored -> {DEST.name}")


if __name__ == "__main__":
    main()
