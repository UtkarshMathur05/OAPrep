# Frontend — React + TypeScript + Vite

## Run

```bash
cd frontend
cp .env.example .env
npm install
npm run dev          # http://localhost:5173
```

## Start here

**[docs/FRONTEND_ROADMAP.md](../docs/FRONTEND_ROADMAP.md)** — build order (F0–F8),
state shape, per-screen acceptance criteria, and the provenance rendering spec.

## Working without a backend

`VITE_USE_MOCK=true` (the default) makes every function in
[src/services/api.ts](src/services/api.ts) resolve from
[src/data/mockData.ts](src/data/mockData.ts) after a short delay. Build the whole
UI this way, then set `VITE_USE_MOCK=false` to hit FastAPI on
`VITE_API_BASE_URL`.

## Rules

- HTTP only. No AI logic, no database access, no direct Judge0 calls.
- All requests go through `services/api.ts`.
- All API shapes live in `types/index.ts` and mirror `backend/app/schemas/`.

## Layout

```
src/
  components/  VoiceRecorder, MemoryCard, CandidateList, ConfidenceScore,
               ProblemDisplay, CodeEditor, TestResults
  pages/       Home, Reconstruct, Practice
  services/    api.ts (axios + mock switch)
  types/       index.ts (shared interfaces)
  data/        mockData.ts
```
