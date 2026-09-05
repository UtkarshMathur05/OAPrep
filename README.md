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

| Layer | Stack |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Monaco Editor, Axios |
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| AI / RAG | Google Gemini (text + embeddings), pgvector |
| Database | PostgreSQL 16 + pgvector (Docker Compose) |
| Execution | Judge0 API |

## Folder structure

```
recollect/
├── frontend/          React app — UI only, talks to the backend over HTTP
├── backend/           FastAPI — REST API, orchestrates AI, DB and Judge0
├── ai/                Gemini pipeline — extraction, retrieval, reconstruction
├── database/          SQL schema + seed, run by Docker Compose
├── docs/              API contract and architecture notes
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

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
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

## Scope

36-hour hackathon MVP. No auth, no microservices, no Kubernetes, no custom
sandbox. Working end-to-end flow beats architectural polish.
