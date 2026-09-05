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
