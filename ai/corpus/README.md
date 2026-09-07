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
| 5. Signatures | `python -m ai.corpus.fetch_signatures` | network + Postgres | ~70 min |
| 6. Functional | `python -m ai.corpus.load_signatures --apply` | Postgres | ~30s |
| 7. Dump | `python -m ai.corpus.load_signatures --dump` | Postgres | ~5s |

Intermediate files land in `ai/corpus/out/` (gitignored). There are two final
artifacts and **both are committed**: `database/init/03_corpus.sql` so nobody
re-embeds, and `database/init/10_signatures.sql` so nobody re-fetches. Step 5
costs 1,125 requests to a site entitled to rate-limit us, and without its dump a
fresh clone browses 987 problems it cannot run.

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

**5. `fetch_signatures.py`** — pulls the typed function signature (`metaData`),
the real example inputs (`exampleTestcaseList`) and per-language starters
(`codeSnippets`) for every problem already in the database.

This is what lets a problem be solved by writing the function the statement
describes rather than a stdin parser. The statements were always written for a
signature — "given an array `nums` and an integer `target`" says nothing about
which line the target is on, because upstream there are no lines — so running
them over stdin meant every problem told the reader one thing and the runner
another.

**6. `load_signatures.py`** — converts a problem to `exec_mode='functional'`
and replaces its stdin test cases with JSON ones.

The one guessy step in the whole pipeline lives here. LeetCode publishes example
*inputs* but not expected *answers*, so the answers are read from the `Output:`
lines of the statement and paired positionally. A problem converts only when
everything corroborates: the signature parses, every type has a harness, the
counts match, each input carries exactly one JSON value per parameter, and each
answer parses as JSON of the declared return type. Anything else stays on stdin
and is reported.

**987 of 1,125 convert (88%).** The other 138 — 137 skipped here, plus the one
community-contributed problem, which has no upstream signature at all — divide
into groups that are worth keeping distinct, because only one of them is work:

| Left on stdin | Count | Why |
| --- | --- | --- |
| class-design problems (LRU Cache, Min Stack) | 53 | no single function to call |
| database questions | 44 | the answer is SQL; there is no function |
| answers that are not JSON | 16 | the `Output:` line is prose, or an in-place `nums = [1,1,2,_]` |
| premium-locked | 10 | the signature is public, the starter code is not |
| `metaData` param-count mismatch | 7 | `metaData` does not describe the real function |
| JavaScript-track | 5 | starters exist only for languages with no harness |
| unpairable examples | 2 | input and `Output:` counts disagree |

Only the third and last groups are recoverable, and only case by case. The first
two need a third execution mode; premium starters would have to be invented; and
a param-count mismatch is the guard working, not failing.

The conversion is **self-healing**: a problem already `functional` that no longer
passes these checks is reverted to stdin and its cases deleted, because leaving
it converted means every run fails for a reason the person cannot see.

A problem left behind still works exactly as it did. A problem converted with a
mispaired answer would tell people their correct solution is wrong, which is the
failure this pipeline is built to refuse.

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
