# Backend — FastAPI

Central API layer. Talks to the `ai/` package, PostgreSQL and Judge0; returns
clean JSON to the frontend. No frontend code lives here.

## Run

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs · health check: `/health`

Environment comes from the repo-root `.env` (copy `.env.example` first).

## Layout

```
app/
  main.py        FastAPI app, CORS, router registration
  config.py      env-backed settings
  api/           thin routes: memory, search, reconstruct, verify, problems
  schemas/       Pydantic request/response models (the integration contract)
  models/        dataclasses mirroring the SQL tables
  services/      the actual logic: ai_service, database_service, judge_service
  db/            connection helper + schema bootstrap
```

Keep routes thin — logic goes in `services/`.

## Database access

All queries go through [app/db/database.py](app/db/database.py). Never call
`psycopg.connect` anywhere else.

```python
from app.db.database import query, query_one, execute, get_conn

rows = query("SELECT slug, title FROM problems WHERE difficulty = %s", ("medium",))
one  = query_one("SELECT * FROM problems WHERE slug = %s", ("two-sum",))
new  = execute("INSERT INTO problem_memories (raw_transcript) VALUES (%s) RETURNING id", (text,))

with get_conn() as conn, conn.cursor() as cur:   # multi-statement transaction
    cur.execute(...)
    cur.execute(...)
```

Notes:

* Rows are `dict`s (`row["title"]`), so SELECT column order never matters.
* `get_conn()` commits on clean exit and rolls back on any exception.
* Always pass parameters as `%s` placeholders — never f-string SQL.
* pgvector is registered per connection, so `vector` columns adapt to and from
  Python lists. Reads come back as `pgvector.Vector`; call `.to_list()` for a
  plain list. Cosine distance is the `<=>` operator.
* One connection per unit of work, no pool. A local connect is ~5ms; add
  `psycopg_pool` only if that ever shows up in a profile.

Gotchas worth knowing:

* `save_memory` writes all **seven** Genome fields. `data_structures` and
  `algorithm_hints` were added to `problem_memories` after the initial schema —
  if your `POST /memory` silently drops them, your volume predates that change;
  see [../database/README.md](../database/README.md#schema-changes-after-first-boot).
* `get_problem` accepts a UUID **or** a slug. Two separate SQL placeholders are
  used on purpose: reusing one makes Postgres infer `uuid` from the first use,
  and `slug = $1` then fails with `operator does not exist: text = uuid`.
* Filters build parameterised `WHERE` fragments. Never f-string SQL.

`GET /health/db` reports reachability plus corpus size:

```json
{ "status": "ok", "db": "memoize", "problems": 5, "embedded": 0 }
```

It returns 503 with the driver's message when the database is down.

## Mock mode

`USE_MOCK_AI=true` in `.env` makes `ai_service` and `judge_service` return canned
responses, so every endpoint answers with a correctly shaped payload before the
AI modules and Judge0 are wired up. Flip it to `false` as each service lands.

It only covers the **AI and Judge0** calls — the database layer is always real.
So `POST /memory` returns a mocked genome but persists it and hands back a
genuine UUID, and `/problems` is live against Postgres regardless of the flag.

## Endpoints

See [../docs/API.md](../docs/API.md) for the full contract.

**Status** says what the endpoint actually does right now — `live` is real,
`mocked` returns canned data of the correct shape.

| Method | Path | Purpose | Status |
| --- | --- | --- | --- |
| GET | `/health` | liveness | live |
| GET | `/health/db` | DB reachable + corpus size | live |
| GET | `/problems` | browse corpus; `limit`/`offset`/`difficulty`/`company`/`search` | live |
| GET | `/problems/{id}` | one problem, **by UUID or slug** | live |
| POST | `/memory` | transcript → Genome, persisted | **live** when a key is set, else mocked |
| GET | `/memory/{id}` | read back a stored genome | live |
| POST | `/search` | genome → ranked candidates | mocked |
| POST | `/reconstruct` | memory + candidate → full problem | mocked |
| POST | `/verify` | code → Judge0 results | **live** |

`/problems` returns `{total, limit, offset, problems[]}` — `total` is the count
matching the filters, not the page size. `companies` on each row is sliced to 5
for display; `company_count` is the true total.

`/problems/{id}` uses **`ProblemSummary`/`ProblemDetail`, not the `Problem`
shape from `/reconstruct`**. A corpus row is stored text; a reconstructed
problem also carries `constraints`, `examples`, `confidence` and `provenance`,
which Gemini produces at reconstruct time and which are not columns.

## Code execution (Judge0)

Setup options and API gotchas: **[../docs/JUDGE0.md](../docs/JUDGE0.md)**.

`POST /verify` runs real code. Flow:

```
/verify -> resolve problem (uuid or slug) -> load <=5 test cases
        -> POST /submissions/batch  (one request, all cases)
        -> poll GET /submissions/batch until every status.id > 2
        -> compare stdout to expected_output, rstrip'd
        -> save to `submissions` -> VerifyResponse
```

Notes from the live API, worth knowing before you change anything:

* `time` is a **string** in seconds (`"0.011"`); `memory` is an **int in KB**.
* `stdout` always has a trailing newline — hence `rstrip()` on both sides.
* The batch endpoint returns **201**, and does **not** support `wait=true`;
  it must be polled. Status ids 1 and 2 are queued/processing.
* Judge0 reports `Accepted` when the program merely *ran*. We never send it an
  `expected_output`, so correctness is decided here — a run can be `Accepted`
  by Judge0 and still be `Wrong Answer` to us.
* On failure, `actual_output` falls back to stderr/compile output so the UI can
  show why.
* Python only (`LANGUAGE_IDS`). Other languages return a message, not an error.
* Network failure degrades to a `Judge0 unavailable: ...` status, never a 500.

## Test cases

Two sources, in order of trust.

**1. Reconstruction examples (primary).** `/reconstruct` stores its own examples
as test cases. They are already stdin/stdout, already shown to the user, and
cost **no extra model request** — the reconstruction prompt pins the format, so
they cannot drift from what is on screen.

**2. Cold generation (fallback).** When `/verify` finds a problem with no cases
— one the user never reconstructed — it generates them, then **validates them by
execution**:

```
generate_suite()  -> reference_solution + N candidate cases
judge_service.run_reference(solution, inputs)  -> what the code actually prints
keep only cases where actual == claimed        -> store those
```

Asking for answers alone does not work. Measured on `two-sum`, one case put the
target first, another put it last, and a third was wrong under either reading —
a correct solution would have failed whichever convention it picked. Requiring a
reference solution fixes the format (the model has to write a parser) and
running it catches the arithmetic: 4 of 5 cases kept, the wrong one dropped.

Generation happens **once per problem ever** — `save_test_cases` is idempotent on
`(problem_id, input)`, and the next visit reads the rows back.

If every case fails validation the endpoint reports `No test cases for this
problem` rather than storing something untrustworthy. A wrong expected output is
worse than none: it tells someone their correct solution is broken.

## Error handling

Handlers live in [app/errors.py](app/errors.py), registered most-specific-first.
Nothing escapes as a bare 500, and every response carries an actionable `hint`.

| Failure | Status | Response |
| --- | --- | --- |
| Postgres unreachable | 503 | "Database unavailable." + `docker compose up -d` |
| Other `psycopg.Error` | 500 | names the type; points at a stale volume for a missing column |
| Judge0 / Gemini failure | 502 | suggests `USE_MOCK_AI=true` |
| `NotImplementedError` | 501 | "not implemented yet" + how to fall back to mocks |
| Anything else | 500 | logged with traceback; the client gets a message, never internals |

**Startup guard:** `USE_MOCK_AI=false` with no `GEMINI_API_KEY` refuses to boot
rather than failing on the first request mid-demo. `.env.example` placeholders
(`your_..._here`) count as unset, so a copied-but-unedited `.env` is caught.

`GET /health` reports both flags:

```json
{ "status": "ok", "mock_ai": true, "ai_ready": false }
```

## Tests

```bash
cd backend && ../venv/bin/python -m pytest tests -q
```

25 integration tests. They need Postgres (`docker compose up -d`) but **never**
call Gemini or Judge0 — both are monkeypatched, so the suite is fast, free and
runs without an API key.

What they cover: response shapes, every filter, pagination, UUID-or-slug lookup,
404-not-500 on malformed ids, the seven-field genome round-trip, the real
extraction path with Gemini stubbed, the no-key fallback, and Judge0 degrading
instead of crashing.

They earn their keep: the first run caught `ModuleNotFoundError: ai` — uvicorn
starts from `backend/`, so `import ai.*` did not resolve. `app/__init__.py` now
puts the repo root on `sys.path`. That would otherwise have surfaced the moment
someone added a real key.

### Remaining backend tasks

| Task | Scope | Blocked by |
| --- | --- | --- |
| B10a | ~~`/memory` → `ai.extraction`~~ **done** | — |
| B10b | `/search` → `ai.retrieval` | `embeddings.py`, `vector_search.py`, `reranker.py` are stubs |
| B10c | `/reconstruct` → `ai.reconstruction` | `reconstruct.py` is a stub |
| B10d | test-case generation | `ai/verification/test_generator.py` is a stub |

**`/memory` is live.** Set `GEMINI_API_KEY` and `USE_MOCK_AI=false` to use it.
With no key it falls back to the mock rather than failing, so a teammate without
one still gets a correctly shaped response.

Done: B1 connection helper · B2 schema split · B3–B4 corpus browse ·
B5 memory persistence · B6 test cases + submissions · B7–B8 Judge0 ·
B9 error handling.
