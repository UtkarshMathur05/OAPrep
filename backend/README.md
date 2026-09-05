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

`GET /health/db` reports reachability plus corpus size:

```json
{ "status": "ok", "db": "recollect", "problems": 5, "embedded": 0 }
```

It returns 503 with the driver's message when the database is down.

## Mock mode

`USE_MOCK_AI=true` in `.env` makes `ai_service` and `judge_service` return canned
responses, so every endpoint answers with a correctly shaped payload before the
AI modules and Judge0 are wired up. Flip it to `false` as each service lands.

## Endpoints

See [../docs/API.md](../docs/API.md) for the full contract.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/memory` | transcript → Problem Genome |
| POST | `/search` | genome → ranked candidates |
| POST | `/reconstruct` | memory + candidate → full problem |
| POST | `/verify` | code + language → Judge0 results |
| GET | `/problems` | list corpus problems |
| GET | `/problems/{id}` | one problem |
| GET | `/health` | liveness |
