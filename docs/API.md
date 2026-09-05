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
    "examples": [{ "input": "...", "output": "...", "explanation": "..." }],
    "confidence": 0.91,
    "provenance": {
      "title": "retrieved",
      "description": "retrieved",
      "constraints": "inferred",
      "examples": "inferred"
    },
    "notes": [
      "You weren't sure about obstacles; this problem has none."
    ],
    "starter_code": "class Solution:\n    def minPathSum(self, grid): ..."
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
| `search` | — | case-insensitive title match |

Ordered by `popularity` descending — the corpus ranking, so the most commonly
asked problems come first.

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
      "recency": "3mo"
    }
  ]
}
```

`total` is the count matching the filters, not the page size.

## GET /problems/{id}

Accepts **either a UUID or a slug**, so `/problems/two-sum` works.

Returns one `ProblemSummary` plus `description`, `has_embedding` (whether it is
searchable yet) and `test_case_count`. `404` with `{"detail": "..."}` when absent.

> This is **not** the same shape as `/reconstruct`'s `problem`. A corpus row is
> stored text; a reconstructed problem carries `constraints`, `examples` and
> `confidence`, which Gemini produces at reconstruct time and which are not
> columns. Two shapes, deliberately.

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
