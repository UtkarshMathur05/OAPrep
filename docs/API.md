# API Contract

Base URL (dev): `http://localhost:8000` · Interactive docs: `/docs`

This file is the **integration boundary** between the three developers. Change it
only by agreement — then update `backend/app/schemas/` and
`frontend/src/types/index.ts` to match.

---

## POST /memory

Extract a Problem Genome from a raw transcript.

**Request**
```json
{ "transcript": "I remember a problem where I had a grid..." }
```

**Response**
```json
{
  "memory_id": "mock-memory-1",
  "memory": {
    "concepts": ["grid", "dynamic programming"],
    "operations": ["right", "down"],
    "objective": "minimize cost",
    "constraints": [],
    "data_structures": [],
    "algorithm_hints": [],
    "uncertainties": ["obstacles"]
  }
}
```

---

## POST /search

Retrieve and rerank candidate problems for a genome.

**Request**
```json
{
  "memory": { "concepts": ["grid", "dynamic programming"], "objective": "minimize cost" },
  "memory_id": "mock-memory-1",
  "top_k": 5,
  "companies": ["google"]
}
```

`companies` is optional. When present it filters the corpus *before* the vector
search (`WHERE companies @> ARRAY[...]`), which is a large win: "it was a Google
question" cuts 3,399 candidates to 2,325. Lowercase slugs, matching the directory
names under `data/leetcode-companywise-interview-questions/`.

**Response**
```json
{
  "candidates": [
    {
      "id": "123",
      "title": "Minimum Path Sum",
      "confidence": 0.91,
      "difficulty": "medium",
      "topics": ["Array", "Dynamic Programming", "Matrix"],
      "companies": ["amazon", "google", "microsoft"],
      "company_count": 41,
      "reason": "Grid with down/right moves, minimizing a sum."
    }
  ]
}
```

`confidence` is 0.0–1.0, sorted descending.

`topics`, `companies` and `company_count` come from the corpus and are there for
the UI to render — "asked at Google, Amazon and 39 others" is a credible, free
detail on a candidate card. `companies` is truncated to the top few by the
backend; `company_count` is the true total.

---

## POST /reconstruct

Rebuild the full problem statement from a memory and the chosen candidate.

**Request**
```json
{ "memory_id": "123", "candidate_id": "456" }
```

**Response**
```json
{
  "problem": {
    "id": "456",
    "title": "Minimum Path Sum",
    "description": "...",
    "constraints": ["1 <= m, n <= 200"],
    "examples": [
      { "input": "3 3\n1 3 1\n1 5 1\n4 2 1", "output": "7", "explanation": "..." }
    ],
    "confidence": 0.91,
    "provenance": {
      "title": "retrieved",
      "description": "inferred",
      "constraints": "retrieved",
      "examples": "inferred"
    },
    "notes": [
      "You recalled obstacles; this problem has none — you may be thinking of Unique Paths II."
    ],
    "starter_code": "import sys\n\ndef main():\n    ..."
  }
}
```

### provenance

Maps a field name to how that field came to be known:

| Value | Meaning |
| --- | --- |
| `remembered` | the user said it |
| `retrieved` | it came from the stored corpus row |
| `inferred` | the model supplied it; the user never said it |

Expected keys are the problem's own content fields — `title`, `description`,
`constraints`, `examples`. **A missing key means the pipeline made no claim**;
render it unlabelled rather than defaulting to a value.

This is CLAUDE.md §19 made machine-readable, and it is the difference between
reconstruction and "printing the stored description". Screen 4 should make the
three levels visually distinct — an inferred constraint must never look like
something the user remembered.

*Known limitation:* the map is keyed by field, so it cannot say that
`constraints[0]` is remembered while `constraints[1]` is inferred. Per-item
provenance would need `Dict[str, List[Provenance]]`. Fine for the MVP; worth
revisiting only if the demo needs it.

### notes

Free-text caveats for the reconstruction screen — conflicts between the memory
and the matched problem, details that were filled in, things left uncertain.

### starter_code

Seeds the Monaco buffer on the Practice screen. Python only (§9). `null` when
the pipeline produced none; the editor should fall back to an empty buffer.

All three fields are **additive and default to empty**, so a client that ignores
them still works.

### Examples are stdin/stdout

`input` is the literal text the solution reads on standard input; `output` is
exactly what it must print. Not function-call shorthand — Judge0 executes a
script, not a method (§9), and `starter_code` is written to match.

---

## Identity

Every request may carry an `X-Session-Id` header holding a UUID the browser
generates once and keeps. It identifies a **browser, not a person** — there is
no authentication yet — and it is what runs, submissions and contributions are
attributed to.

Omitting it is supported everywhere: the call still works, it just accumulates
no progress. A malformed value degrades to anonymous rather than `400`-ing a
request that would otherwise succeed.

> Server-side this is resolved in exactly one place, `app/identity.py`. When
> accounts land, that function starts returning a user id and no other module
> changes — which is why the column exists now rather than later.

---

## GET /languages

Every language a solution can be written in, with the starter program for it.

```json
[
  { "id": "python", "label": "Python 3", "monaco": "python", "starter": "import sys\n..." },
  { "id": "cpp", "label": "C++", "monaco": "cpp", "starter": "#include <bits/stdc++.h>\n..." }
]
```

The starter lives server-side so the editor and the runner can never disagree
about the calling convention. `monaco` is the editor's own language id, for
syntax highlighting.

**Adding a language costs a Judge0 id and a starter template — nothing else.**
Because a solution is a whole program over stdin/stdout rather than a function
body, the stored test cases are identical for every language, so a new one
needs no driver and no regenerated cases.

---

## GET /progress

What the calling session has done, for marking a listing in one request.

```json
{ "solved": ["triangle"], "attempted": ["two-sum"], "runs": 12, "solved_count": 1 }
```

Slugs, not ids, because that is what the listing and the URLs use.

## GET /progress/{id}

The calling session's standing on one problem. Accepts a UUID or a slug.

```json
{ "runs": 4, "submissions": 1, "solved": true, "best_passed": 2, "total": 2 }
```

---

## POST /verify

Run submitted code against the problem's test cases via Judge0.

**Request**
```json
{ "problem_id": "123", "code": "...", "language": "java" }
```

Supported `language` values: `python`, `java`, `cpp`, `c`, `javascript`, `typescript`.

**Response**
```json
{
  "status": "Accepted",
  "passed": 12,
  "total": 12,
  "runtime": "0.21s",
  "memory": "18MB",
  "results": [
    { "index": 0, "passed": true, "input": "...", "expected_output": "...", "actual_output": "..." }
  ]
}
```

`status` mirrors Judge0: `Accepted`, `Wrong Answer`, `Time Limit Exceeded`,
`Compilation Error`, `Runtime Error`.

---

## GET /problems

Browse the known-problem corpus.

**Query parameters** — all optional:

| Param | Default | Notes |
| --- | --- | --- |
| `limit` | 20 | 1–100 |
| `offset` | 0 | pagination |
| `difficulty` | — | `easy` / `medium` / `hard` |
| `company` | — | lowercase slug, e.g. `google`; GIN-indexed |
| `search` | — | case-insensitive match on title **or** statement |
| `topic` | — | LeetCode tag, verbatim casing: `Dynamic Programming`; GIN-indexed |
| `origin` | — | `corpus` (LeetCode dump) or `community` (user-contributed) |
| `sort` | `popularity` | `popularity` / `title` / `difficulty` / `companies` / `acceptance` / `newest` |

Default order is `popularity` descending — the corpus ranking, so the most
commonly asked problems come first. `sort` is matched against a whitelist
server-side; an unknown value silently falls back to `popularity` rather than
erroring, because a stale bookmark should still render a page.

`companies` is ranked by how much of the corpus each company asks, then sliced
to five. The stored array is alphabetical, so slicing it raw put "Accenture,
Accolite, Adobe" on every row — accurate and useless.

**Response**
```json
{
  "total": 1200,
  "limit": 20,
  "offset": 0,
  "problems": [
    {
      "id": "1fa55ea2-04b0-477d-ac38-8605a476e032",
      "slug": "minimum-path-sum",
      "title": "Minimum Path Sum",
      "difficulty": "medium",
      "platform": "leetcode",
      "source_url": "https://leetcode.com/problems/minimum-path-sum/",
      "topics": ["Array", "Dynamic Programming", "Matrix"],
      "companies": ["amazon", "google", "microsoft"],
      "company_count": 41,
      "popularity": 812.5,
      "acceptance": 64.1,
      "recency": "3mo",
      "origin": "corpus",
      "confidence": 1.0,
      "contribution_count": 0
    }
  ]
}
```

`total` is the count matching the filters, not the page size.

## GET /problems/{id}

Accepts **either a UUID or a slug**, so `/problems/two-sum` works.

Returns one `ProblemSummary` plus `description`, `exec_mode`, `signature`,
`code_snippets`, `runnable_languages`, `io_format`, `has_embedding` (whether it
is searchable yet) and `test_case_count`.

`exec_mode` decides how the problem is solved:

* `"functional"` — write the method the statement describes. `signature` is
  LeetCode-shaped `{name, params, return}`, `code_snippets` maps our language id
  to that problem's starter, and `io_format` is empty because there is no stdin
  to describe.
* `"stdin"` — write a whole program. `io_format` states what it reads;
  `signature` is null and `code_snippets` is empty.

`runnable_languages` is what the editor must offer. A functional problem needs
both a starter and a harness for a language, so the list is usually shorter than
the eleven in `GET /languages`; a stdin problem lists all of them.

`io_format` is the stdin contract in prose, e.g.

```
Line 1: two integers m and n, the number of rows and columns.
Next m lines: n integers each, the grid rows.
Output: a single integer, the minimum path sum.
```

Solutions here are whole programs reading stdin, not function bodies, so this is
load-bearing: a statement written for a function signature never says which line
the target is on. Empty string when no format has been pinned down — render
nothing rather than a guess. `POST /reconstruct` returns the same field on its
`problem`. `404` with `{"detail": "..."}` when absent.

> This is **not** the same shape as `/reconstruct`'s `problem`. A corpus row is
> stored text; a reconstructed problem carries `constraints`, `examples` and
> `confidence`, which Gemini produces at reconstruct time and which are not
> columns. Two shapes, deliberately.

## GET /problems/facets

Every browse axis with its counts, in one request. This is what the sidebar,
the company directory and the topic directory all read.

```json
{
  "companies": [{ "name": "google", "count": 1009 }],
  "topics": [{ "name": "Array", "count": 636 }],
  "difficulties": [{ "name": "easy", "count": 296 }],
  "totals": { "problems": 1124, "community": 0, "companies": 608, "topics": 143 }
}
```

`companies` is capped at 80 entries and `topics` at 40 — the tail is a long
drizzle of one-problem companies that adds scrolling, not information. `totals`
carries the true, uncapped counts.

> Declared **before** `/problems/{id}` in the router, or `facets` is read as an
> identifier and 404s.

---

## POST /contribute/match

Step one of contributing: check whether the corpus already has what the user is
describing. Runs the same extract → retrieve → rerank pipeline as `/memory` +
`/search`, but tolerates finding nothing — "we don't have this" is the answer
that sends the user on to create it.

**Request**
```json
{ "transcript": "a robot collecting shelves, K kilos per trip…", "top_k": 5 }
```

**Response**
```json
{
  "memory_id": "…",
  "memory": { "concepts": ["greedy"], "…": [] },
  "candidates": [{ "id": "…", "title": "Watering Plants", "confidence": 0.85 }],
  "likely_duplicate": true
}
```

`likely_duplicate` is `true` when the top candidate scores ≥ 0.75. It is a
default, not a block — the UI still offers "none of these".

## POST /contribute

Step two: either corroborate an existing problem or write a new one.

**Request** — send `confirm_problem_id` to corroborate, omit it to create:
```json
{
  "transcript": "…",
  "details": {
    "title": "Warehouse robot trips",
    "difficulty": "medium",
    "topics": ["Greedy"],
    "companies": ["zoho"],
    "input_format": "First line n and K, then n lines of position and weight",
    "output_format": "A single integer",
    "example": "…",
    "constraints": "n up to 10^5"
  },
  "confirm_problem_id": null
}
```

Every field of `details` is optional. Anything left blank is inferred by Gemini
while drafting the statement, and every inference is appended to the stored
description under "Assumed while writing this up" rather than presented as
fact — CLAUDE.md §19, applied to the corpus itself.

**Response**
```json
{
  "problem_id": "4abb036c-…",
  "slug": "warehouse-robot-trip-minimization",
  "title": "Warehouse Robot Trip Minimization",
  "action": "created",
  "confidence": 0.35,
  "contribution_count": 1,
  "test_case_count": 1,
  "message": "Added as a community problem at 35% confidence. …"
}
```

### The confidence rule

A community problem is an inference until other people independently describe
the same thing, so trust is a stored number rather than an assumption:

```text
confidence = min(0.95, 0.35 + 0.15 × (contribution_count − 1))
```

One account is 0.35. Each further description adds 0.15, capped at 0.95 — a
community statement never becomes as trustworthy as one fetched from LeetCode.
Corpus rows sit at 1.0 and do not move: a user agreeing with a LeetCode
statement is not new evidence about that statement. The contribution is still
recorded, because it tells us which corpus problems people actually
half-remember.

Creation refuses rather than half-succeeding in two places. An empty drafted
statement returns `422` — a blank statement would match everything in retrieval.
A failed embedding returns `503` and saves nothing — a row with no vector exists
but is invisible to recall, which is the most confusing possible outcome.

## GET /health

```json
{ "status": "ok" }
```

---

## Errors

Standard FastAPI shape:

```json
{ "detail": "Problem not found" }
```

`422` for validation failures, `404` for missing resources, `502` when Gemini or
Judge0 fails upstream.
