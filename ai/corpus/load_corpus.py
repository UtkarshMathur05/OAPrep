"""Corpus step 4 — embed the corpus and load it into Postgres.

Joins out/index.jsonl with out/descriptions.jsonl, embeds each problem once with
Gemini, upserts into `problems`, and optionally writes the whole thing to
database/init/03_corpus.sql so the team can restore it without re-embedding.

    python -m ai.corpus.load_corpus            # embed + load
    python -m ai.corpus.load_corpus --dump     # also write 03_corpus.sql
    python -m ai.corpus.load_corpus --dump --skip-load   # no Postgres needed
    python -m ai.corpus.load_corpus --from-dump-only   # skip embedding entirely

Commit the dump. Embedding 1,200 problems three times is a waste of the shared
Gemini quota, and a fresh clone should get working retrieval for free.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from ai.gemini_client import AIError, embed_batch, is_daily_quota

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).parent / "out"
DUMP = REPO_ROOT / "database" / "init" / "03_corpus.sql"
BATCH = 32
# Free tier: 100 embed requests/minute, and one batch of 32 texts counts as
# 32 requests. Pace proactively rather than bouncing off the limit.
EMBEDS_PER_MINUTE = 90

UPSERT = """
INSERT INTO problems (
    slug, leetcode_id, title, description, platform, difficulty, source_url,
    topics, companies, company_count, popularity, acceptance, recency,
    description_source, embedding
) VALUES (
    %(slug)s, %(leetcode_id)s, %(title)s, %(description)s, 'leetcode',
    %(difficulty)s, %(url)s, %(topics)s, %(companies)s, %(company_count)s,
    %(popularity)s, %(acceptance)s, %(recency)s, %(source)s, %(embedding)s
)
ON CONFLICT (slug) DO UPDATE SET
    description        = EXCLUDED.description,
    topics             = EXCLUDED.topics,
    companies          = EXCLUDED.companies,
    company_count      = EXCLUDED.company_count,
    popularity         = EXCLUDED.popularity,
    acceptance         = EXCLUDED.acceptance,
    recency            = EXCLUDED.recency,
    description_source = EXCLUDED.description_source,
    embedding          = EXCLUDED.embedding;
"""


def embed_text_for(row: dict) -> str:
    """What actually gets embedded.

    Title and topics are repeated ahead of the body on purpose: a vague memory
    names concepts and data structures far more often than it quotes statement
    prose, so those tokens deserve the weight.
    """
    topics = ", ".join(row.get("topics") or [])
    body = (row.get("description") or "")[:4000]
    return f"{row['title']}\nTopics: {topics}\nDifficulty: {row.get('difficulty')}\n\n{body}"


def join_rows() -> list[dict]:
    index = [json.loads(l) for l in (OUT_DIR / "index.jsonl").read_text().splitlines() if l.strip()]
    descs: dict[str, dict] = {}
    for line in (OUT_DIR / "descriptions.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        # Later records win, so a gapfill supersedes an earlier "locked" marker.
        if rec.get("description") or rec["slug"] not in descs:
            descs[rec["slug"]] = rec

    rows = []
    for row in index:
        d = descs.get(row["slug"])
        if not d or not d.get("description"):
            continue  # no text, nothing to embed
        rows.append({**row,
                     "description": d["description"],
                     "topics": d.get("topics") or [],
                     "source": d.get("source")})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dump", action="store_true", help="also write database/init/03_corpus.sql")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-load", action="store_true",
                    help="embed and dump without touching Postgres (no Docker needed)")
    args = ap.parse_args()

    rows = join_rows()
    if args.limit:
        rows = rows[: args.limit]
    print(f"{len(rows)} problems have text and will be embedded")

    pace = BATCH / EMBEDS_PER_MINUTE * 60
    for start in range(0, len(rows), BATCH):
        chunk = rows[start:start + BATCH]
        began = time.monotonic()
        try:
            vectors = embed_batch([embed_text_for(r) for r in chunk])
        except AIError as exc:
            if not is_daily_quota(exc):
                raise
            # Out of embeddings until tomorrow. Dump what we have rather than
            # leaving the team with no corpus at all (CLAUDE.md §20); the cache
            # means a re-run tomorrow only embeds the remainder.
            print(f"\n  daily embedding quota reached at {start}/{len(rows)}.")
            print("  Dumping what is embedded so far; re-run tomorrow to finish.")
            break
        for row, vec in zip(chunk, vectors):
            row["embedding"] = vec
        done = min(start + BATCH, len(rows))
        print(f"  embedded {done}/{len(rows)}", flush=True)

        elapsed = time.monotonic() - began
        # Cache hits cost no quota, so only pace when we actually called the API.
        if elapsed > 1.0 and done < len(rows):
            time.sleep(max(0.0, pace - elapsed))

    embedded = [r for r in rows if r.get("embedding")]
    if len(embedded) != len(rows):
        print(f"{len(rows) - len(embedded)} problems have no embedding yet and are excluded")
    rows = embedded

    # Generating the dump is pure text formatting, so it must not require a
    # database. That keeps the AI lane independent of Dev 3's docker-compose:
    # commit 03_corpus.sql and `docker compose up` loads it from database/init/.
    if args.skip_load:
        print("skipping database load (--skip-load)")
    else:
        dsn = os.getenv("DATABASE_URL")
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            for row in rows:
                cur.execute(UPSERT, {**row, "embedding": str(row["embedding"])})
            conn.commit()
        print(f"loaded {len(rows)} problems into {dsn.rsplit('@', 1)[-1]}")

    if args.dump:
        DUMP.parent.mkdir(parents=True, exist_ok=True)
        with DUMP.open("w", encoding="utf-8") as fh:
            fh.write("-- Generated by ai/corpus/load_corpus.py --dump. Do not edit by hand.\n")
            fh.write("-- Commit this: it saves every teammate a full re-embed.\n\n")
            for row in rows:
                cols = ("slug", "leetcode_id", "title", "description", "difficulty",
                        "url", "topics", "companies", "company_count", "popularity",
                        "acceptance", "recency", "source", "embedding")
                vals = []
                for c in cols:
                    v = row.get(c)
                    if v is None:
                        vals.append("NULL")
                    elif isinstance(v, list):
                        if c == "embedding":
                            vals.append("'" + str(v) + "'")
                        else:
                            inner = ",".join('"' + str(x).replace('"', '\\"') + '"' for x in v)
                            vals.append("'{" + inner + "}'")
                    elif isinstance(v, (int, float)):
                        vals.append(str(v))
                    else:
                        vals.append("'" + str(v).replace("'", "''") + "'")
                fh.write(
                    "INSERT INTO problems (slug,leetcode_id,title,description,difficulty,"
                    "source_url,topics,companies,company_count,popularity,acceptance,"
                    "recency,description_source,embedding) VALUES ("
                    + ",".join(vals) + ") ON CONFLICT (slug) DO NOTHING;\n"
                )
        size_mb = DUMP.stat().st_size / 1e6
        print(f"wrote {DUMP.relative_to(REPO_ROOT)} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
