# Task Split

Three developers, one branch each. Everything below is written so nobody waits on
anybody — mock layers at every boundary make that true (see "Never blocked").

| Branch | Owner | Owns |
| --- | --- | --- |
| `frontend` | Dev 1 | `frontend/` |
| `ai` | Dev 2 | `ai/` |
| `backend` | Dev 3 | `backend/`, `database/`, `docker-compose.yml` |

---

## Do this first, together (hour 0)

One person runs it; everyone benefits.

- [ ] `cp .env.example .env`, add a `GEMINI_API_KEY`
- [ ] `docker compose up -d`, confirm `psql` connects
- [ ] **Run the corpus pipeline** — [ai/corpus/README.md](../ai/corpus/README.md)
- [ ] **Commit `database/init/03_corpus.sql`**

> Retrieval returns nothing until this exists, which means no candidates, no
> reconstruction, no demo. It is the one task that blocks two of the three
> developers, so it goes first and it gets done once — not three times.

Steps 3 and 4 of that pipeline are **untested**; they need a live API key and a
running Postgres. Budget an hour for first-run bugs, especially the pgvector
insert format in `load_corpus.py`.

---

## Dev 1 — Frontend (`frontend` branch)

> **Step-by-step build order, state shape and per-screen acceptance criteria:
> [FRONTEND_ROADMAP.md](FRONTEND_ROADMAP.md).** Start there; the checklist below
> is the summary.

Set `VITE_USE_MOCK=true` and build the whole thing against
`src/data/mockData.ts`. You need nothing else from anyone.

- [ ] `npm install`, confirm `npm run dev` serves on :5173
- [ ] Single-page stepper — one `step` state, not four routes. Every step needs
      the previous step's data, so routing costs more than it gives.
- [ ] `VoiceRecorder` — Web Speech API (`webkitSpeechRecognition`), textarea fallback
- [ ] `MemoryCard` — render the genome, and make the **uncertainties visually
      distinct** (`✓ Grid` vs `? Obstacles uncertain`). This is the screen that
      shows Recollect handles doubt; it is the product's whole differentiator.
- [ ] `CandidateList` + `ConfidenceScore` — show `reason`, `topics`, and
      "asked at Google, Amazon and 39 others" from `company_count`
- [ ] Optional company filter chip, feeding `companies` on `POST /search`
- [ ] `ProblemDisplay` — mark which parts are reconstructed vs. retrieved
- [ ] `CodeEditor` — Monaco, Python only
- [ ] `TestResults` — pass/fail summary
- [ ] Empty and error states for every stage (§20)
- [ ] Flip `VITE_USE_MOCK=false` and integrate

**Never touch:** Gemini, Postgres, Judge0, API keys. All HTTP goes through
`src/services/api.ts`.

---

## Dev 2 — AI / RAG (`ai` branch)

Every module takes and returns Pydantic models, so each is testable from a REPL
with a hand-built `ProblemGenome`. Only retrieval needs Postgres running.

- [ ] Own the corpus pipeline through to a committed `03_corpus.sql`
- [ ] `extraction/genome.py` — transcript → `ProblemGenome`
- [ ] Use Gemini **structured output** (`response_schema=ProblemGenome`), never
      "return JSON" in the prompt plus regex repair
- [ ] Tune `extraction_prompt.txt` so hedged details land in `uncertainties`,
      not `constraints` — the whole demo rests on this distinction
- [ ] `retrieval/embeddings.py` — wrap `gemini_client.embed*`
- [ ] `retrieval/vector_search.py` — `ORDER BY embedding <=> %s LIMIT k`, with
      the optional `companies @> ARRAY[...]` pre-filter
- [ ] `retrieval/reranker.py` — one Gemini call over the whole shortlist; use
      `popularity` as a tiebreaker
- [ ] `reconstruction/reconstruct.py` — genome + candidate → full statement
- [ ] `verification/test_generator.py` — **stdin/stdout format**, ≤5 cases
- [ ] Disk-cache every Gemini response, keyed by input hash — this is what makes
      the live demo instant and deterministic

**Never:** import FastAPI, or build an agent framework. Plain functions.

---

## Dev 3 — Backend / Infra (`backend` branch)

Start with `USE_MOCK_AI=true` — every endpoint already returns correctly-shaped
canned data, so Dev 1 can integrate against you on day one. Replace the mocks one
service at a time as Dev 2 lands modules.

- [ ] Confirm `uvicorn app.main:app --reload` and `/docs` work
- [ ] `db/database.py` — `psycopg` connection helper
- [ ] `database_service.py` — problems, memories, test cases, submissions
- [ ] `db/init_db.py` — re-apply schema without nuking the volume
- [ ] Wire `ai_service.py` to the real `ai.*` modules as they land
- [ ] Persist the genome in `POST /memory`, return a real `memory_id`
- [ ] `judge_service.py` — Judge0 **batch** endpoint, Python only, ≤5 cases,
      explicit `httpx` timeout
- [ ] `GET /problems` with company/difficulty filters
- [ ] Error handling: Gemini failure, bad AI output, empty results, Judge0
      timeout — a useful message, never a 500 (§20)

Setup options: **[JUDGE0.md](JUDGE0.md)**.

**Judge0 is the likeliest demo-day failure.** The public CE instance is
rate-limited and often down. Keep the mock path working, and treat Judge0 as the
last milestone, not the first.

---

## Never blocked

```text
Frontend   VITE_USE_MOCK=true   full UI, no backend
Backend    USE_MOCK_AI=true     shaped responses, no AI
AI         Pydantic in/out      testable in a REPL, no server
```

## Integration order

```text
M0  corpus           ← blocks M2, M3
M1  environment      everyone runs everything
M2  memory → genome  first real end-to-end slice
M3  retrieval        candidates + confidence on screen
M4  reconstruction   the payoff screen
M5  Judge0           last, because it is the flakiest
```

## Changing a contract

`docs/API.md`, `backend/app/schemas/`, and `frontend/src/types/index.ts` change
**together**, in one commit, and you tell the other two. Additive changes are
cheap; renames are not.
