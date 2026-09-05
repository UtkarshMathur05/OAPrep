# Recollect

Reconstruct the coding problem you can't quite remember.

You describe a half-remembered problem ("there was a grid, you could only move
right or down, and you had to minimize something"). Recollect extracts what you
actually remember, searches a corpus of known problems, reranks the matches,
rebuilds the full statement, and then lets you solve and verify it in the browser.

---

## Architecture

```
Browser (React + Vite, :5173)
    |  HTTP / JSON only
    v
FastAPI (:8000)
    |            \
    |             \--> Judge0 (code execution)
    v
ai/ package  ---> Gemini API
    |
    v
PostgreSQL + pgvector (:5432, Docker)
```

Pipeline: **memory → extraction → retrieval → reranking → reconstruction → code → verification**.

More detail in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tech stack

| Layer | Stack | Scoped for 36 hours |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind v3, Monaco, Axios | Single-page stepper; Web Speech API for voice |
| Backend | Python, FastAPI, Pydantic, Uvicorn | Sync endpoints, raw SQL via `psycopg` — no ORM |
| AI / RAG | Gemini 2.5 Flash + `gemini-embedding-001` | Native `response_schema` output; disk-cached |
| Database | PostgreSQL 16 + pgvector (Docker) | Exact vector scan, no ANN index |
| Execution | Judge0 API | Python only, batch endpoint, 5 test cases |

### Why these narrowings

Each one removes hours of work without removing anything the demo shows.

- **Python-only execution.** Judge0 speaks stdin/stdout; coding problems are
  function-signature shaped. Every extra language needs its own driver that parses
  stdin, calls the function, and prints the result. One language, one template.
- **stdin/stdout problem format, decided up front.** `test_cases.input` is
  literally what Judge0 receives; `expected_output` is compared to stdout. Change
  this late and every generated test case has to be regenerated.
- **Gemini structured output.** `response_schema` with a Pydantic model, rather
  than asking for JSON in the prompt and repairing what comes back.
- **No ANN index.** At 500–5000 problems an exact scan is ~2ms, while `ivfflat`
  with the usual `lists=100` measurably *hurts* recall.
- **Disk-cached AI calls.** The demo path becomes instant, deterministic, and
  survives the venue wifi.
- **Web Speech API.** Browser-native; record-upload-transcribe is hours of backend
  work for no visible difference.
- **One venv for `backend/` + `ai/`.** The backend imports `ai.*` anyway.

Full rationale and the fallback ladder: [CLAUDE.md §28](CLAUDE.md).

## Folder structure

```
recollect/
├── frontend/          React app — UI only, talks to the backend over HTTP
├── backend/           FastAPI — REST API, orchestrates AI, DB and Judge0
├── ai/                Gemini pipeline — extraction, retrieval, reconstruction
├── database/          SQL schema + seed, run by Docker Compose
├── data/              LeetCode company-wise question CSVs (source corpus)
├── docs/              API contract, architecture notes, task split
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## Installation

```bash
git clone <repo-url> recollect
cd recollect
cp .env.example .env        # then fill in GEMINI_API_KEY
```

### 1. Database

```bash
docker compose up -d
```

Creates the tables, the `vector` extension and a few seed problems on first boot.
Data persists in the `pgdata` volume. See [database/README.md](database/README.md).

> **The corpus is the critical path.** Retrieval returns nothing until the
> problem corpus is loaded *and embedded*. If `database/init/03_corpus.sql` is
> already committed, `docker compose up -d` loads it for you and you are done.
> If not, someone has to run the pipeline below — once, for the whole team.

### 1b. Corpus (only if `database/init/03_corpus.sql` is missing)

`data/leetcode-companywise-interview-questions/` holds 3,399 unique problems
across 660 companies — but only titles, no problem statements. The pipeline in
`ai/corpus/` ranks them, fetches the real statements, and embeds them.

```bash
python -m ai.corpus.build_index --limit 1200   # ~2s,  no network, no key
python -m ai.corpus.fetch_descriptions         # ~30m, network, resumable
python -m ai.corpus.gapfill                    # ~5m,  needs GEMINI_API_KEY
python -m ai.corpus.load_corpus --dump         # ~5m,  needs key + Postgres
```

**Commit the `--dump` output.** Re-embedding 1,200 problems on three machines
wastes the shared Gemini quota for no benefit. Details:
[ai/corpus/README.md](ai/corpus/README.md).

### 2. Backend + AI

One virtualenv covers both — the backend imports `ai.*` directly.

```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt -r ai/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
```

http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

http://localhost:5173

---

## Environment variables

Copy `.env.example` to `.env`. **Never commit `.env`** — it is gitignored.

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Google Gemini key ([aistudio.google.com](https://aistudio.google.com/apikey)) |
| `GEMINI_TEXT_MODEL` | Default `gemini-2.5-flash` |
| `GEMINI_EMBEDDING_MODEL` | Default `gemini-embedding-001` |
| `EMBEDDING_DIM` | Must match `problems.embedding VECTOR(n)` — default `768` |
| `DATABASE_URL` | `postgresql://recollect:recollect@localhost:5432/recollect` |
| `POSTGRES_USER` / `_PASSWORD` / `_DB` / `_PORT` | Consumed by `docker-compose.yml` |
| `JUDGE0_URL` | `https://ce.judge0.com`, or a RapidAPI/self-hosted instance |
| `JUDGE0_API_KEY` / `JUDGE0_API_HOST` | Only for RapidAPI |
| `CORS_ORIGINS` | Comma-separated allowed origins (no wildcard) |
| `USE_MOCK_AI` | `true` → backend returns canned AI/Judge0 responses |

The frontend reads its own `frontend/.env` (`VITE_API_BASE_URL`, `VITE_USE_MOCK`);
only `VITE_*` variables reach the browser, so never put a key there.

---

## API documentation

Full contract: [docs/API.md](docs/API.md). Live schema: http://localhost:8000/docs

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/memory` | transcript → Problem Genome |
| POST | `/search` | genome → ranked candidates + confidence |
| POST | `/reconstruct` | memory + candidate → full problem statement |
| POST | `/verify` | code + language → Judge0 pass/fail |
| GET | `/problems`, `/problems/{id}` | browse the corpus |
| GET | `/health` | liveness |

---

## Splitting the work

Task-by-task breakdown, with owners and the order things unblock in:
**[docs/TASKS.md](docs/TASKS.md)**.

Per-area detail: **[docs/FRONTEND_ROADMAP.md](docs/FRONTEND_ROADMAP.md)** (Dev 1),
**[ai/corpus/README.md](ai/corpus/README.md)** (Dev 2, Milestone 0),
**[backend/README.md](backend/README.md)** (Dev 3),
**[docs/JUDGE0.md](docs/JUDGE0.md)** (code execution setup).

## Git workflow

Four branches, one owner each:

| Branch | Owner | Scope |
| --- | --- | --- |
| `main` | shared | integration; only merged, working code |
| `frontend` | Dev 1 | `frontend/` |
| `ai` | Dev 2 | `ai/` |
| `backend` | Dev 3 | `backend/`, `database/` |

```bash
git checkout frontend        # your own branch
git pull origin main         # rebase on integration regularly
# ...work...
git push origin frontend     # open a PR into main
```

Nobody waits on anyone else:

- **Frontend** runs on mock data (`VITE_USE_MOCK=true`).
- **Backend** returns correctly-shaped canned responses (`USE_MOCK_AI=true`).
- **AI** modules are plain functions over Pydantic models, testable in isolation.

`docs/API.md` is the contract. Changing a payload shape means editing that file,
`backend/app/schemas/`, and `frontend/src/types/index.ts` together — and telling
the other two.

## Failure ladder

Every layer degrades into the one below rather than showing a blank screen:

```text
Live Gemini + live Judge0     ideal
  ↓  Gemini slow / rate-limited
Cached AI responses           the golden demo path
  ↓  Judge0 down
USE_MOCK_AI=true              canned, correctly shaped
  ↓  backend down
VITE_USE_MOCK=true            frontend alone still demos the whole flow
```

Judge0 is the likeliest thing to break on the day — the public CE instance is
rate-limited and often down, and self-hosting wants privileged containers you do
not want to debug at hour 30. Keep the mock path working.

## Scope

36-hour hackathon MVP. No auth, no microservices, no Kubernetes, no ORM, no
migrations, no vector index, no deployment, no custom sandbox. Working
end-to-end flow beats architectural polish.
