"""Corpus step 1 — fold 1,642 company CSVs into one ranked problem index.

Reads data/leetcode-companywise-interview-questions/<company>/*.csv and emits
ai/corpus/out/index.jsonl: one row per unique problem, with the companies that
asked it, a popularity score, and the most recent bucket it appeared in.

No network, no API key. Run this first.

    python -m ai.corpus.build_index --limit 1200
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "leetcode-companywise-interview-questions"
OUT_DIR = Path(__file__).parent / "out"

# Most recent bucket wins. all.csv is the superset we aggregate over; the others
# only tell us how recently a problem was asked.
RECENCY_RANK = {
    "thirty-days.csv": 4,
    "three-months.csv": 3,
    "six-months.csv": 2,
    "more-than-six-months.csv": 1,
}
RECENCY_LABEL = {4: "30d", 3: "3mo", 2: "6mo", 1: "older", 0: "unknown"}


def _pct(value: str) -> float:
    """'57.8%' -> 57.8, tolerating blanks and junk."""
    try:
        return float(value.strip().rstrip("%"))
    except (ValueError, AttributeError):
        return 0.0


def _slug(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def build(limit: int | None) -> list[dict]:
    problems: dict[str, dict] = {}
    companies: dict[str, set[str]] = defaultdict(set)
    # Popularity = sum of per-company Frequency %, i.e. asked often AND widely.
    score: dict[str, float] = defaultdict(float)
    recency: dict[str, int] = defaultdict(int)

    company_dirs = sorted(d for d in DATA_DIR.iterdir() if d.is_dir() and not d.name.startswith("."))

    for company_dir in company_dirs:
        company = company_dir.name
        for csv_path in sorted(company_dir.glob("*.csv")):
            is_all = csv_path.name == "all.csv"
            bucket = RECENCY_RANK.get(csv_path.name, 0)

            with csv_path.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    url = (row.get("URL") or "").strip()
                    title = (row.get("Title") or "").strip()
                    if not url or not title:
                        continue
                    slug = _slug(url)

                    if slug not in problems:
                        problems[slug] = {
                            "slug": slug,
                            "leetcode_id": int(row["ID"]) if (row.get("ID") or "").strip().isdigit() else None,
                            "title": title,
                            "url": url,
                            "difficulty": (row.get("Difficulty") or "").strip().lower() or None,
                            "acceptance": _pct(row.get("Acceptance %", "")),
                        }

                    recency[slug] = max(recency[slug], bucket)
                    # Aggregate over all.csv only — the recency files are subsets
                    # of it, so counting them too would double-weight.
                    if is_all:
                        companies[slug].add(company)
                        score[slug] += _pct(row.get("Frequency %", ""))

    rows = []
    for slug, problem in problems.items():
        asked_by = sorted(companies[slug])
        rows.append({
            **problem,
            "companies": asked_by,
            "company_count": len(asked_by),
            "popularity": round(score[slug], 2),
            "recency": RECENCY_LABEL[recency[slug]],
        })

    rows.sort(key=lambda r: (-r["popularity"], -r["company_count"], r["title"]))
    return rows[:limit] if limit else rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=1200,
                    help="keep only the N most popular problems (0 = all)")
    args = ap.parse_args()

    rows = build(args.limit or None)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "index.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    by_diff: dict[str, int] = defaultdict(int)
    for r in rows:
        by_diff[r["difficulty"] or "unknown"] += 1

    print(f"wrote {len(rows)} problems -> {out.relative_to(REPO_ROOT)}")
    print("  difficulty:", dict(by_diff))
    print("  top 5:")
    for r in rows[:5]:
        print(f"    {r['popularity']:>8.1f}  {r['company_count']:>3} cos  {r['title']}")


if __name__ == "__main__":
    main()
