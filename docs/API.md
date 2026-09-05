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
    "confidence": 0.91
  }
}
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

## GET /problems · GET /problems/{id}

Browse the known-problem corpus. Returns the same `problem` object shape as
`/reconstruct` (a bare object, or an array for the list form).

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
