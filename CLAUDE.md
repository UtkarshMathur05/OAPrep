# Recollect — Claude Code Project Context

## 1. Project Overview

**Recollect** is an AI-powered system that helps users reconstruct coding problems they remember but cannot fully recall.

The core problem:

> A developer remembers a coding problem vaguely — perhaps the algorithm, data structure, or a few details — but cannot remember the exact problem statement.

Instead of searching manually through hundreds of coding problems, the user describes what they remember.

Recollect:

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

Recollect helps recover it.

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

The important distinction is that Recollect is NOT simply:

> "Search coding problems using keywords."

It is also NOT simply:

> "Ask an LLM to guess a coding problem."

Instead, Recollect separates the process into stages.

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

Recollect executes the solution against test cases and shows:

```text
Accepted
12 / 12 tests passed
Runtime: 0.21s
```

---

# 4. MVP

The minimum successful Recollect demo is:

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

### Screen 1 — Recollect

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

This demonstrates that Recollect understands uncertainty.

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

> **Make Recollect's core "I vaguely remember a coding problem → Recollect finds and reconstructs it" experience work reliably and look impressive.**

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
                         RECOLLECT
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

This is the canonical architecture for the Recollect hackathon MVP.
