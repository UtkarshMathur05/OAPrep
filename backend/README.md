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
{ "status": "ok", "db": "recollect", "problems": 5, "embedded": 0 }
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
| POST | `/memory` | transcript → Genome, persisted | genome mocked, **saved for real** |
| GET | `/memory/{id}` | read back a stored genome | live |
| POST | `/search` | genome → ranked candidates | mocked |
| POST | `/reconstruct` | memory + candidate → full problem | mocked |
| POST | `/verify` | code → Judge0 results | mocked |

`/problems` returns `{total, limit, offset, problems[]}` — `total` is the count
matching the filters, not the page size. `companies` on each row is sliced to 5
for display; `company_count` is the true total.

`/problems/{id}` uses **`ProblemSummary`/`ProblemDetail`, not the `Problem`
shape from `/reconstruct`**. A corpus row is stored text; a reconstructed
problem also carries `constraints`, `examples`, `confidence` and `provenance`,
which Gemini produces at reconstruct time and which are not columns.

### Remaining backend tasks

| Task | Scope |
| --- | --- |
| B6 | `get_test_cases`, `save_submission` |
| B7–B8 | Judge0: one submission, then batch + aggregate |
| B9 | error handling — no bare 500s (§20) |
| B10 | swap `ai_service` mocks for real `ai.*` calls (needs Dev 2) |
