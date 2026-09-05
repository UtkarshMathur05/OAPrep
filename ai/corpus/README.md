# Corpus pipeline (Milestone 0)

Turns `data/leetcode-companywise-interview-questions/` into an embedded,
searchable corpus in Postgres. **Retrieval returns nothing until this has run.**

Run from the repo root, in order.

| Step | Command | Needs | Time |
| --- | --- | --- | --- |
| 1. Rank | `python -m ai.corpus.build_index --limit 1200` | nothing | ~2s |
| 2. Fetch | `python -m ai.corpus.fetch_descriptions` | network | ~30 min |
| 3. Gapfill | `python -m ai.corpus.gapfill` | `GEMINI_API_KEY` | ~5 min |
| 4. Load | `python -m ai.corpus.load_corpus --dump` | key + Postgres | ~5 min |

Intermediate files land in `ai/corpus/out/` (gitignored). The final artifact is
`database/init/03_corpus.sql` — **commit it**, so nobody else re-embeds.

## What each step does

**1. `build_index.py`** — folds 1,642 CSVs across 660 companies into one row per
unique problem (3,399 total), aggregating the companies that asked it and summing
per-company `Frequency %` into a `popularity` score. Sorts by popularity and
keeps the top N. The top of that ranking is Two Sum, LRU Cache, Valid Parentheses
— exactly the problems people half-remember, which is the point.

Only `all.csv` feeds the aggregate; the recency files are subsets of it and would
double-count. They set the `recency` flag instead (`30d` / `3mo` / `6mo` / `older`).

**2. `fetch_descriptions.py`** — the CSVs have no problem text, only titles, so
this pulls real statements from LeetCode's public GraphQL endpoint and flattens
the HTML to plain text. Also captures `topicTags`. Stdlib only, so it runs before
any venv exists. Resumable — Ctrl-C and re-run freely; finished slugs are skipped.

Premium-locked problems serve no content and are recorded as `source: "locked"`.

**3. `gapfill.py`** — has Gemini write statements for the locked ones. If Gemini
does not recognise a problem it returns `UNKNOWN` and the row is left without
text rather than filled with a plausible-sounding fabrication; `load_corpus`
then skips it. An honest gap beats a wrong problem in the corpus.

**4. `load_corpus.py`** — joins index + descriptions, embeds in batches of 32,
and upserts on `slug`. What gets embedded is title + topics + difficulty + body,
with title and topics first: a vague memory names concepts and data structures
far more often than it quotes statement prose, so those tokens deserve the weight.

## Why the company data matters

`problems.companies` and `problems.popularity` come free with this dataset and
are worth more than they look:

- **Filter** — "it was a Google interview question" cuts 3,399 candidates to
  2,325 before the vector search runs: `WHERE companies @> ARRAY['google']`
  (GIN-indexed).
- **Prior** — `popularity` is a good tiebreaker in reranking. Between two
  candidates that fit the memory equally well, the one 126 companies ask is the
  more likely memory.
- **Demo** — "asked at Google, Amazon and 124 others" on a candidate card is a
  concrete, credible detail that costs nothing to render.

## Re-running

Steps 2–4 are all resumable or idempotent. To rebuild from scratch,
`rm -rf ai/corpus/out/` and start at step 1.
