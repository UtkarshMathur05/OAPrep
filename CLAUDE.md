# Memoize — Claude Code Project Context

## 1. Project Overview

**Memoize** is an AI-powered system that helps users reconstruct coding problems they remember but cannot fully recall.

The core problem:

> A developer remembers a coding problem vaguely — perhaps the algorithm, data structure, or a few details — but cannot remember the exact problem statement.

Instead of searching manually through hundreds of coding problems, the user describes what they remember.

Memoize:

```text
User's vague memory
        ↓
Speech / Text
        ↓
AI Memory Extraction
        ↓
Problem Genome
        ↓
Semantic Retrieval
        ↓
Candidate Problems
        ↓
AI Reranking
        ↓
Problem Reconstruction
        ↓
User Verification
        ↓
Code Editor
        ↓
Generated / Known Test Cases
        ↓
Code Execution
        ↓
Verification Result
```

The product should feel like:

> "I remember this coding problem, but I don't remember what it was."

Memoize helps recover it.

---

# 2. Hackathon Context

This is a **3-person, 36-hour hackathon project**.

The project must prioritize:

1. A working end-to-end demo
2. Strong technical novelty
3. Clear AI usage
4. Reliable integration
5. Good UI/UX
6. A compelling demonstration

Do NOT optimize for production-grade infrastructure.

Do NOT over-engineer.

A smaller working system is much more valuable than a theoretically perfect architecture that does not work during the demo.

---

# 3. Core Product Concept

The important distinction is that Memoize is NOT simply:

> "Search coding problems using keywords."

It is also NOT simply:

> "Ask an LLM to guess a coding problem."

Instead, Memoize separates the process into stages.

### Stage 1 — Memory

Capture what the user actually remembers.

Example:

> "I remember a grid problem where you had to move right or down and find the minimum cost. I think there were some obstacles, but I'm not sure."

### Stage 2 — Problem Genome

Convert the vague memory into structured information.

Example:

```json
{
  "concepts": [
    "grid",
    "dynamic programming"
  ],
  "operations": [
    "move right",
    "move down"
  ],
  "objective": "minimize cost",
  "data_structures": [],
  "algorithm_hints": [
    "dynamic programming"
  ],
  "constraints": [],
  "uncertainties": [
    "whether obstacles exist",
    "exact grid constraints"
  ]
}
```

The system should explicitly preserve uncertainty instead of pretending that uncertain details are facts.

### Stage 3 — Retrieval

Use semantic embeddings to retrieve potentially related problems.

The system should retrieve several candidates rather than immediately choosing one.

Example:

```text
1. Minimum Path Sum       91%
2. Unique Paths           72%
3. Dungeon Game           64%
4. Path With Minimum Effort 51%
```

### Stage 4 — Reranking

Use the structured memory and candidate metadata to determine which candidate best matches the user's recollection.

The AI should compare:

* concepts
* operations
* objective
* constraints
* data structures
* algorithm hints
* uncertainty

### Stage 5 — Reconstruction

If the original problem is not an exact match, reconstruct the most likely version based on:

```text
User memory
+
Retrieved candidate
+
Known problem information
```

The system must distinguish between:

* remembered facts
* retrieved facts
* reconstructed/inferred facts

This distinction is important.

### Stage 6 — Verification

The user can write a solution.

Memoize executes the solution against test cases and shows:

```text
Accepted
12 / 12 tests passed
Runtime: 0.21s
```

---

# 4. MVP

The minimum successful Memoize demo is:

```text
Input memory
      ↓
Problem Genome
      ↓
Top candidate problems
      ↓
Confidence
      ↓
Reconstructed problem
      ↓
Code editor
      ↓
Run tests
      ↓
Result
```

Everything else is secondary.

If time becomes limited, prioritize the above flow.

---

# 5. Technology Stack

## Frontend

Use:

* React
* TypeScript
* Vite
* Tailwind CSS
* Monaco Editor
* Axios

Responsibilities:

* User interface
* Voice/text input UI
* Memory display
* Candidate problem display
* Confidence visualization
* Reconstructed problem display
* Code editor
* Test results
* API communication

The frontend must NOT contain:

* database logic
* Gemini API keys
* AI prompts
* retrieval logic
* Judge0 credentials

**Hackathon decisions:**

* Voice input uses the **browser Web Speech API** (`webkitSpeechRecognition`), not
  audio upload + server transcription. Zero backend work; Chrome-only is fine for
  a demo. A textarea is always the fallback.
* The recall flow is **one page with a `step` state**, not four routes. The flow
  is linear and every step needs the previous step's data — routing would mean
  serializing genome/candidates/problem between routes for no benefit.
* Tailwind v3 (not v4). Better-documented, and every snippet you'll paste at
  hour 30 assumes it.
* Monaco loads from a CDN by default. If the venue wifi is unreliable, vendor it
  (`loader.config({ paths: { vs: '/vs' } })`).

---

# 6. Backend

Use:

* Python
* FastAPI
* Pydantic
* Uvicorn

Responsibilities:

* REST API
* request validation
* orchestration
* database communication
* AI service communication
* Judge0 communication
* response formatting

The backend is the main integration layer.

Architecture:

```text
React
  ↓
FastAPI
  ├── AI services
  ├── PostgreSQL
  └── Judge0
```

Keep API routes thin.

Business logic should live in service modules.

---

# 7. AI / RAG

Use:

* Google Gemini API
* Gemini embeddings where appropriate
* Python
* PostgreSQL
* pgvector

Do not use a complicated agent framework unless absolutely necessary.

Prefer normal Python services and clear function calls.

AI responsibilities:

1. Memory extraction
2. Problem Genome creation
3. Embedding generation
4. Vector retrieval
5. Candidate reranking
6. Problem reconstruction
7. Test generation

**Hackathon decisions:**

* Use Gemini's **native structured output** — `response_mime_type="application/json"`
  plus `response_schema=<PydanticModel>` — never "return JSON" in the prompt text
  followed by regex repair. This removes a whole class of parse failures.
* Model: `gemini-2.5-flash` everywhere. Do not reach for a larger model; latency
  during a live demo matters more than marginal quality.
* Cache every AI response to disk, keyed by a hash of the input. The golden demo
  path then runs instantly, deterministically, and offline.
* Embeddings: `gemini-embedding-001` at 768 dimensions. Batch them; the free tier
  is rate-limited per minute.

---

# 8. Database

Use:

* PostgreSQL
* pgvector

Run PostgreSQL through Docker Compose.

Initial tables:

## problems

```text
id
title
description
platform
difficulty
source_url
embedding
created_at
```

## problem_memories

```text
id
problem_id
concepts
operations
constraints
objective
uncertainties
raw_transcript
created_at
```

## test_cases

```text
id
problem_id
input
expected_output
created_at
```

## submissions

```text
id
problem_id
code
language
status
runtime
memory
created_at
```

Do not create unnecessary tables during the hackathon.

### Corpus metadata on `problems`

The corpus comes from `data/leetcode-companywise-interview-questions/`, so
`problems` also carries `slug` (unique upsert key), `leetcode_id`, `topics[]`
(LeetCode topicTags), `companies[]`, `company_count`, `popularity` (summed
per-company Frequency %), `acceptance`, `recency` and `description_source`.

These are columns, not tables — no join, no schema sprawl. `companies` is
GIN-indexed for `WHERE companies @> ARRAY['google']`.

**Do not add an ANN index.** At hackathon corpus size (500–5000 problems) an exact
scan is ~2ms, while an `ivfflat` index with the usual `lists=100` *reduces* recall
for no measurable gain. Plain `ORDER BY embedding <=> %s LIMIT k` is correct here.

Use raw SQL with `psycopg`. No SQLAlchemy, no Alembic — the schema is four tables
that change by editing one `.sql` file.

---

# 9. Code Execution

Use Judge0.

The architecture is:

```text
Frontend
   ↓
FastAPI
   ↓
Judge0
   ↓
FastAPI
   ↓
Frontend
```

The frontend must NEVER directly call Judge0.

The backend should be responsible for:

* submitting code
* specifying language
* passing test cases
* polling for results if necessary
* normalizing results
* returning a simple response to the frontend

Example:

```json
{
  "status": "Accepted",
  "passed": 12,
  "total": 12,
  "runtime": "0.21s",
  "memory": "18MB"
}
```

Do not build a custom code execution sandbox during the hackathon.

**Hackathon decisions:**

* **Python only** for the MVP. Judge0 takes stdin and returns stdout, but coding
  problems are function-signature shaped — so each language needs its own driver
  that parses stdin, calls the function, and prints the result. One language means
  one template; four means four, plus four sets of edge cases. List other
  languages as future work.
* **Standardize on stdin/stdout now**, before test-case generation starts.
  `test_cases.input` is exactly what Judge0 receives on stdin;
  `expected_output` is compared to stdout after trailing-whitespace stripping.
  Deciding this late means regenerating every test case.
* Use the **batch endpoint** (`POST /submissions/batch`) — one HTTP round trip for
  all test cases, not one per case.
* **Cap test cases at 5.** The public CE instance is aggressively rate-limited.
* Judge0 is the **most likely thing to fail on demo day**: the public instance is
  often down, and self-hosting needs privileged containers and cgroup setup you do
  not want to debug at hour 30. Keep `USE_MOCK_AI=true` working as a fallback, and
  set an explicit `httpx` timeout on every call.

---

# 10. Repository Structure

The intended structure is:

```text
recollect/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── VoiceRecorder.tsx
│   │   │   ├── MemoryCard.tsx
│   │   │   ├── CandidateList.tsx
│   │   │   ├── ConfidenceScore.tsx
│   │   │   ├── ProblemDisplay.tsx
│   │   │   ├── CodeEditor.tsx
│   │   │   └── TestResults.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Reconstruct.tsx
│   │   │   └── Practice.tsx
│   │   │
│   │   ├── services/
│   │   │   └── api.ts
│   │   │
│   │   ├── types/
│   │   │   └── index.ts
│   │   │
│   │   ├── data/
│   │   │   └── mockData.ts
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── memory.py
│   │   │   ├── search.py
│   │   │   ├── reconstruct.py
│   │   │   ├── verify.py
│   │   │   └── problems.py
│   │   │
│   │   ├── models/
│   │   │   ├── problem.py
│   │   │   ├── memory.py
│   │   │   └── submission.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── memory.py
│   │   │   ├── search.py
│   │   │   ├── reconstruct.py
│   │   │   └── verify.py
│   │   │
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── database_service.py
│   │   │   └── judge_service.py
│   │   │
│   │   └── db/
│   │       ├── database.py
│   │       └── init_db.py
│   │
│   ├── requirements.txt
│   └── README.md
│
├── ai/
│   ├── extraction/
│   │   └── genome.py
│   │
│   ├── retrieval/
│   │   ├── embeddings.py
│   │   ├── vector_search.py
│   │   └── reranker.py
│   │
│   ├── reconstruction/
│   │   └── reconstruct.py
│   │
│   ├── verification/
│   │   └── test_generator.py
│   │
│   ├── prompts/
│   │   ├── extraction_prompt.txt
│   │   ├── reranking_prompt.txt
│   │   └── reconstruction_prompt.txt
│   │
│   ├── models/
│   │   └── problem_genome.py
│   │
│   ├── requirements.txt
│   └── README.md
│
├── database/
│
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── DEMO.md
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

# 11. Three-Person Team Ownership

The project has three developers.

## Developer 1 — Frontend

Primary ownership:

```text
frontend/
```

Responsibilities:

* React application
* Tailwind UI
* voice input
* memory visualization
* candidate results
* confidence visualization
* reconstructed problem
* Monaco editor
* verification UI

Developer 1 should work with mock API data whenever backend functionality is not ready.

---

## Developer 2 — AI / RAG

Primary ownership:

```text
ai/
```

Responsibilities:

* Gemini integration
* Problem Genome
* prompts
* embeddings
* vector retrieval
* reranking
* reconstruction
* test generation

Developer 2 should make AI modules independently testable.

---

## Developer 3 — Backend / Infrastructure

Primary ownership:

```text
backend/
database/
docker-compose.yml
```

Responsibilities:

* FastAPI
* PostgreSQL
* pgvector
* database schema
* API endpoints
* Judge0 integration
* deployment/integration
* CORS
* environment configuration

---

# 12. Git Workflow

Branches:

```text
main
frontend
ai
backend
```

Developers should primarily work on their own branches.

Never directly break `main`.

Changes to shared API contracts, schemas, or database structures must be communicated to the entire team.

Commit frequently with meaningful messages.

Examples:

```text
feat: add memory extraction endpoint
feat: add candidate problem UI
feat: add pgvector search
fix: handle Judge0 timeout
```

Avoid huge commits containing unrelated changes.

---

# 13. API Contract

The initial API contract is:

## POST /memory

Request:

```json
{
  "transcript": "I remember a problem about a grid..."
}
```

Response:

```json
{
  "memory": {
    "concepts": [
      "grid",
      "dynamic programming"
    ],
    "operations": [
      "right",
      "down"
    ],
    "objective": "minimize cost",
    "uncertainties": [
      "obstacles"
    ]
  }
}
```

---

## POST /search

Request:

```json
{
  "memory": {
    "concepts": [
      "grid",
      "dynamic programming"
    ],
    "objective": "minimize cost"
  }
}
```

Response:

```json
{
  "candidates": [
    {
      "id": "123",
      "title": "Minimum Path Sum",
      "confidence": 0.91
    },
    {
      "id": "456",
      "title": "Unique Paths",
      "confidence": 0.72
    }
  ]
}
```

---

## POST /reconstruct

Request:

```json
{
  "memory_id": "123",
  "candidate_id": "456"
}
```

Response:

```json
{
  "problem": {
    "title": "Minimum Path Sum",
    "description": "...",
    "constraints": [],
    "examples": []
  }
}
```

---

## POST /verify

Request:

```json
{
  "problem_id": "123",
  "code": "...",
  "language": "java"
}
```

Response:

```json
{
  "status": "Accepted",
  "passed": 12,
  "total": 12,
  "runtime": "0.21s",
  "memory": "18MB"
}
```

### Amendments

`POST /search` has since gained two additive fields, documented in `docs/API.md`:

* request: optional `companies: string[]` — corpus filter applied before the
  vector search
* response: `topics`, `companies` and `company_count` on each candidate, for the
  UI to render

Additive only; existing clients are unaffected.

Do not casually change these contracts.

If a change is necessary, update:

```text
docs/API.md
```

and notify the team.

---

# 14. Environment Variables

Use:

```text
GEMINI_API_KEY=
DATABASE_URL=
JUDGE0_URL=
```

Potential additional variables may be added if necessary.

Never commit:

```text
.env
```

Always update:

```text
.env.example
```

when adding a new required environment variable.

The full set is documented in `.env.example` and the root `README.md`. Beyond the
three above, the ones that matter are `USE_MOCK_AI` (canned backend responses),
`EMBEDDING_DIM` (must match the `VECTOR(n)` column), and `CORS_ORIGINS`.

Only `VITE_*` variables reach the browser. Never put a key behind that prefix.

---

# 15. Frontend Mocking Strategy

The frontend must not depend on the AI being complete.

Create:

```text
frontend/src/data/mockData.ts
```

with realistic examples.

Example:

```json
{
  "memory": {
    "concepts": [
      "grid",
      "dynamic programming"
    ],
    "operations": [
      "right",
      "down"
    ],
    "objective": "minimize cost"
  },
  "candidates": [
    {
      "id": "123",
      "title": "Minimum Path Sum",
      "confidence": 0.91
    }
  ]
}
```

The UI should be fully navigable using mock data.

This allows Developer 1 to work independently.

---

# 16. Development Order

Do NOT build everything simultaneously without integration.

Follow these milestones.

## Milestone 0 — Corpus

**This is the real critical path and it is easy to miss.** Retrieval cannot return
anything without an embedded corpus of known problems, which means no candidates,
no reconstruction, and no demo.

The source data is already in the repo: `data/leetcode-companywise-interview-questions/`
holds 3,399 unique problems across 660 companies (41,546 pairs) as CSVs.

**It has no problem statements — only titles.** That is the gap the pipeline in
`ai/corpus/` closes, in four steps:

```text
build_index.py       1,642 CSVs -> 1,200 problems ranked by popularity   ~2s
fetch_descriptions.py  LeetCode GraphQL -> real statements + topicTags   ~30m
gapfill.py             Gemini describes the premium-locked ones          ~5m
load_corpus.py --dump  embed -> Postgres -> database/init/03_corpus.sql  ~5m
```

**Commit `03_corpus.sql`.** Re-embedding on three machines wastes the shared
Gemini quota; a fresh clone plus `docker compose up -d` should give every
developer working retrieval for free.

Full runbook: `ai/corpus/README.md`.

### The company data is a feature

`companies` and `popularity` are worth designing around, not just storing:

* **Filter** — "it was a Google question" prunes 3,399 candidates to 2,325
  *before* the vector search runs. Exposed as the optional `companies` field on
  `POST /search`.
* **Reranking prior** — between two candidates that fit the memory equally well,
  the one 126 companies ask is the likelier memory.
* **Demo** — "asked at Google, Amazon and 124 others" on a candidate card is a
  concrete, credible detail that costs nothing to render.

### Honest gaps over confident fabrication

If Gemini does not recognise a premium-locked problem, `gapfill.py` records no
description and `load_corpus.py` skips the row. A missing problem is recoverable;
a corpus row containing a plausible-sounding invented problem quietly corrupts
retrieval and reconstruction for the rest of the hackathon. This is §19's
certain/uncertain/inferred rule applied to the corpus itself.

---

## Milestone 1 — Environment

Everyone can:

* clone repo
* install dependencies
* start frontend
* start backend
* start PostgreSQL
* access FastAPI docs

---

## Milestone 2 — Independent Components

Frontend:

```text
UI → mock data
```

AI:

```text
Transcript → Problem Genome
```

Backend:

```text
FastAPI → PostgreSQL
```

Judge:

```text
Code → Judge0 → result
```

---

## Milestone 3 — First Integration

Connect:

```text
Frontend
 ↓
FastAPI
 ↓
AI
 ↓
Frontend
```

The user should be able to enter a memory and see an extracted Problem Genome.

---

## Milestone 4 — Retrieval

Connect:

```text
Problem Genome
 ↓
Embedding
 ↓
pgvector
 ↓
Candidate Problems
 ↓
Frontend
```

---

## Milestone 5 — Reconstruction

Connect:

```text
Memory
+
Candidate
 ↓
Gemini
 ↓
Reconstructed Problem
 ↓
Frontend
```

---

## Milestone 6 — Verification

Connect:

```text
Code
 ↓
FastAPI
 ↓
Judge0
 ↓
Tests
 ↓
Result
 ↓
Frontend
```

---

# 17. 36-Hour Priority Plan

## Hours 0–2

All developers:

* agree on architecture
* agree on API contract
* create repository
* create branches
* create environment files
* start Docker/PostgreSQL
* create basic README
* confirm everyone can run the project

Do not spend these two hours designing unnecessary features.

---

## Hours 2–10

Developer 1:

Build the complete frontend shell with mock data.

Developer 2:

Build Gemini memory extraction and Problem Genome.

Developer 3:

Build FastAPI, PostgreSQL, and basic API endpoints.

---

## Hours 10–18

First integration:

```text
Memory
 ↓
AI
 ↓
Backend
 ↓
Frontend
```

Then implement retrieval.

Target:

> User gives a vague memory and sees likely coding problems.

---

## Hours 18–26

Implement:

* reranking
* reconstruction
* test generation
* Judge0
* verification UI

---

## Hours 26–30

Freeze architecture.

Build the complete golden demo.

Do not introduce major new features.

---

## Hours 30–33

Test:

* API failures
* AI failures
* malformed input
* no matching problem
* Judge0 timeout
* incorrect code
* empty memory
* unexpected AI output

Fix only high-impact issues.

---

## Hours 33–36

Stop adding features.

Focus on:

* demo
* slides
* visual polish
* presentation
* rehearsing the story
* preparing answers to technical questions

---

# 18. UX Flow

The ideal user experience:

### Screen 1 — Memoize

Simple introduction:

> "Tell us what you remember."

User can:

* type memory
* speak memory

---

### Screen 2 — Understanding Your Memory

Show:

```text
We found:

✓ Grid
✓ Dynamic Programming
✓ Minimum Cost
✓ Right / Down movement

? Obstacles are uncertain
? Exact constraints are unknown
```

This demonstrates that Memoize understands uncertainty.

---

### Screen 3 — Possible Matches

Show candidate cards:

```text
Minimum Path Sum
91% match

Unique Paths
72% match

Dungeon Game
64% match
```

Explain why the top result matches.

---

### Screen 4 — Reconstructed Problem

Display:

* title
* problem statement
* constraints
* examples
* notes about uncertain/reconstructed details

---

### Screen 5 — Practice

Monaco code editor.

User writes solution.

Click:

```text
Run
```

---

### Screen 6 — Verification

Display:

```text
✓ Accepted

12 / 12 tests passed

Runtime: 0.21s
Memory: 18MB
```

This gives the demo a strong ending.

---

# 19. AI Prompting Principles

AI should produce structured outputs whenever possible.

Prefer:

```text
JSON / Pydantic structured output
```

over free-form responses.

The extraction model should distinguish:

### Certain

Information explicitly remembered by the user.

### Uncertain

Information the user says they are unsure about.

### Inferred

Information the model believes is likely but the user did not explicitly mention.

Never silently turn an inference into a remembered fact.

---

# 20. Error Handling

Every external dependency can fail.

Handle:

* Gemini API failure
* invalid Gemini response
* database failure
* empty search results
* Judge0 failure
* Judge0 timeout
* malformed code
* invalid input

The application should show a useful user-facing error rather than crashing.

During the hackathon, graceful degradation is acceptable.

For example:

If AI retrieval fails:

```text
"We couldn't confidently identify the problem. Try adding another detail."
```

---

# 21. Security

Do not expose:

* Gemini API keys
* database credentials
* Judge0 credentials

to the frontend.

All secrets belong in backend environment variables.

Never commit `.env`.

Do not accept arbitrary dangerous backend commands.

Code execution should go through Judge0.

---

# 22. What NOT to Build

Unless explicitly required later, do NOT add:

* authentication
* user accounts
* payment
* complex dashboards
* social features
* microservices
* Kubernetes
* Redis
* message queues
* custom code sandbox
* complicated agent orchestration
* elaborate CI/CD
* production-grade observability
* an ORM or migration tool (raw SQL is four tables)
* an ANN / vector index (exact scan is fast enough at this size)
* multi-language code execution (Python only)
* server-side speech transcription (the browser does it)
* async/`asyncpg` plumbing — plain `def` endpoints are threadpooled by FastAPI
* deployment; the demo runs on localhost

These are distractions during the hackathon.

---

# 23. Definition of Done

The MVP is considered successful when this complete flow works:

```text
User
 ↓
"I remember a grid problem where..."
 ↓
Problem Genome
 ↓
Candidate Problems
 ↓
Confidence
 ↓
Reconstructed Problem
 ↓
Code Editor
 ↓
Run
 ↓
Judge0
 ↓
Tests
 ↓
Accepted / Failed
```

The frontend must look polished enough for a live demonstration.

The AI must produce useful structured output.

The retrieval system must return plausible candidates.

The verification system must actually execute code.

---

# 24. Engineering Principles

When implementing features, follow these principles:

### Keep it simple

If two implementations work, choose the simpler one.

### Keep boundaries clear

Frontend, backend, AI, and database should remain separated.

### Make failures visible

Do not silently swallow errors.

### Use typed contracts

Use TypeScript types on the frontend and Pydantic schemas on the backend.

### Mock dependencies when useful

Especially during parallel development.

### Don't block other developers

Avoid making unnecessary breaking changes to shared APIs.

### Optimize for the demo

This is a hackathon, not a production deployment.

---

# 25. Instructions for Claude Code

When working on this repository:

1. Read this file before making architectural decisions.
2. Preserve the existing folder structure unless there is a strong reason to change it.
3. Do not introduce new technologies without a clear reason.
4. Do not over-engineer.
5. Follow the API contracts in `docs/API.md`.
6. Keep frontend, backend, AI, and database responsibilities separated.
7. Never hard-code secrets.
8. Update `.env.example` when adding environment variables.
9. Prefer small, focused changes.
10. Do not rewrite unrelated code.
11. If an API contract changes, update `docs/API.md`.
12. If a database schema changes, update the relevant documentation.
13. Maintain mock data so frontend development can continue independently.
14. Test the specific functionality you change.
15. Prioritize the MVP over secondary features.
16. If a requested feature risks the 36-hour timeline, implement the simplest viable version.
17. Do not add authentication or other non-MVP infrastructure unless explicitly requested.
18. Before major architectural changes, explain the tradeoff and keep the team boundaries in mind.

---

# 26. Current Strategic Goal

The single most important goal is:

> **Make Memoize's core "I vaguely remember a coding problem → Memoize finds and reconstructs it" experience work reliably and look impressive.**

The system should demonstrate genuine technical depth through:

* structured memory extraction
* semantic retrieval
* uncertainty handling
* AI-assisted reconstruction
* verification through actual code execution

Do not let secondary features distract from this core experience.

---

# 27. Final Architecture

The intended architecture is:

```text
                         MEMOIZE
                             │
                             ▼
                    ┌─────────────────┐
                    │ React Frontend  │
                    │ TypeScript      │
                    │ Tailwind        │
                    │ Monaco          │
                    └────────┬────────┘
                             │
                             │ REST / JSON
                             ▼
                    ┌─────────────────┐
                    │    FastAPI      │
                    │   API Layer     │
                    └────┬─────┬──────┘
                         │     │
              ┌──────────┘     └────────────┐
              ▼                             ▼
      ┌─────────────────┐          ┌─────────────────┐
      │ AI / RAG        │          │ PostgreSQL      │
      │                 │          │ + pgvector      │
      │ Gemini          │          │                 │
      │ Genome          │          │ Problems        │
      │ Embeddings      │          │ Embeddings      │
      │ Retrieval       │          │ Memories        │
      │ Reranking       │          │ Test Cases      │
      │ Reconstruction  │          │ Submissions     │
      └─────────────────┘          └─────────────────┘
                         │
                         ▼
                  ┌───────────────┐
                  │    Judge0     │
                  │ Code Execution│
                  └───────────────┘
```

This is the canonical architecture for the Memoize hackathon MVP.

---

# 28. Stack Hardening Decisions

The stack in §5–§9 is correct. These are the specific narrowings that make it
buildable in 36 hours, collected in one place. Each removes work without removing
anything the demo shows.

| Decision | Instead of | Why |
| --- | --- | --- |
| Commit an embedded corpus dump | Each dev embeds their own | The corpus is the critical path; build it once |
| Python-only execution | Multi-language | Each language needs its own stdin→function driver |
| stdin/stdout problem format | LeetCode function signatures | Judge0 speaks stdin/stdout; decide before generating tests |
| Judge0 batch endpoint, 5 cases | One request per case | Public CE instance is rate-limited |
| Gemini `response_schema` | "Return JSON" + regex repair | Removes malformed-JSON failures entirely |
| Exact vector scan | `ivfflat` index | ANN hurts recall below ~10k rows |
| Disk cache on AI calls | Live calls during the demo | Instant, deterministic, survives bad wifi |
| Web Speech API | Audio upload + transcription | Hours of backend work for no demo gain |
| One venv for `backend/` + `ai/` | Two venvs, two requirements files | The backend imports `ai.*` anyway |
| Single-page stepper | Four routes | Linear flow; each step needs the previous step's data |
| Raw SQL + `psycopg` | SQLAlchemy + Alembic | Four tables, one `.sql` file |
| Sync `def` endpoints | `async` + `asyncpg` | FastAPI threadpools them; async buys nothing here |

## Degradation ladder

Each stage must fail into the stage below rather than breaking the demo:

```text
Live Gemini + live Judge0        ← ideal
  ↓ Gemini slow or rate-limited
Cached AI responses              ← golden demo path
  ↓ Judge0 down
USE_MOCK_AI=true                 ← canned but correctly-shaped
  ↓ backend down
VITE_USE_MOCK=true               ← frontend alone still demos the full flow
```

Never let a failure at one layer produce a blank screen. §20 applies throughout.

## Where the time actually goes

Budget generously for these; they are consistently underestimated:

1. Building and embedding the corpus (Milestone 0)
2. The stdin/stdout test harness and its driver template
3. Judge0 authentication, rate limits, and result polling
4. Making Gemini output conform reliably to a schema

Budget lightly for the UI shell — mock data means it can be built in parallel
from hour 2 and does not block anything.
