# Architecture

```
Browser (React + Vite, :5173)
    |  HTTP / JSON only
    v
FastAPI (:8000)
    |            \
    |             \--> Judge0 (code execution)
    v
ai/ package  ---> Gemini API (extraction, reranking, reconstruction, embeddings)
    |
    v
PostgreSQL + pgvector (:5432, Docker)
```

## Request flow

1. **`POST /memory`** — transcript → `ai/extraction/genome.py` → `ProblemGenome`,
   saved to `problem_memories`.
2. **`POST /search`** — genome → `ai/retrieval/embeddings.py` embeds the flattened
   genome → `vector_search.py` does a pgvector cosine search over
   `problems.embedding` → `reranker.py` has Gemini score the shortlist.
3. **`POST /reconstruct`** — genome + chosen candidate →
   `ai/reconstruction/reconstruct.py` → full statement with examples.
4. **`POST /verify`** — code + test cases → `judge_service` → Judge0 → aggregated
   pass/fail, written to `submissions`.

## Boundaries

- The frontend only speaks HTTP to FastAPI. It never touches Gemini, Postgres or
  Judge0.
- Routes in `backend/app/api/` stay thin; logic lives in `backend/app/services/`.
- The `ai/` package knows nothing about FastAPI — it takes and returns Pydantic
  models, so each stage is testable on its own.

## Decoupling during the hackathon

- Frontend: `VITE_USE_MOCK=true` → mock data, no backend needed.
- Backend: `USE_MOCK_AI=true` → canned AI/Judge0 responses, correctly shaped.
- AI: modules are importable and testable with a hand-built `ProblemGenome`.
