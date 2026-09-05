# Frontend Roadmap (Dev 1)

Everything here runs on mock data. You need no backend, no database, no API key
until the very last step.

```bash
cd frontend
cp .env.example .env      # VITE_USE_MOCK=true is the default
npm install
npm run dev               # http://localhost:5173
```

If `npm run dev` serves a blank page with no console errors, you're ready — the
router and entry point are already wired.

---

## The one thing that matters

Recollect is not "search for a problem." It is **"I half-remember something,
help me recover it"** — and the product's whole differentiator is that it
distinguishes what you *remembered* from what was *retrieved* from what the
model *inferred* (CLAUDE.md §19).

If the UI renders an inferred constraint identically to something the user
actually said, the demo becomes indistinguishable from printing a stored
description. **F4 and F6 below are the screens that earn the project its
score.** Budget accordingly.

---

## State shape

One page, one state object, a `step` field. Not four routes — every step needs
the previous step's data, and serialising that between routes costs more than
it gives.

```ts
type Step = 'input' | 'memory' | 'candidates' | 'problem' | 'practice'

interface RecallState {
  step: Step
  transcript: string
  memoryId: string | null       // from POST /memory — needed by /reconstruct
  memory: Genome | null
  candidates: Candidate[]
  selected: Candidate | null
  problem: Problem | null
  code: string
  result: VerifyResponse | null
  loading: boolean
  error: string | null
}
```

`useState` in `Reconstruct.tsx` is enough. No Redux, no Zustand, no context —
one component owns this and passes slices down as props.

**Keep `memoryId`.** `POST /reconstruct` takes `{memory_id, candidate_id}`, so
dropping it strands you at step 3.

---

## Build order

Each task is independently demoable. Do them in order — later ones consume
earlier state.

### F0 — Shell (45 min)

`npm install`, confirm dev server, delete the three-route setup in `App.tsx` in
favour of the stepper, add a header and a step indicator.

**Done when:** you can click through all five steps with hardcoded state.

### F1 — Input (1h) · `VoiceRecorder.tsx`

Textarea + submit calling `extractMemory({transcript})`. Then layer in the Web
Speech API:

```ts
const SR = (window as any).webkitSpeechRecognition ?? (window as any).SpeechRecognition
```

Chrome-only is fine. Feature-detect and hide the mic button when absent — never
show a control that silently does nothing.

**Done when:** typing or speaking a memory advances to step 2 with a `memoryId`.

### F2 — Genome display (1.5h) · `MemoryCard.tsx` ⚠️ high value

Currently 7 lines of `JSON.stringify`. Replace with grouped, labelled fields —
and make **uncertainties visually distinct**:

```
We heard:
  ✓ grid          ✓ dynamic programming
  ✓ minimize cost
  ✓ move right    ✓ move down

Still unsure:
  ? whether there were obstacles
```

The `Genome` has seven fields — `concepts`, `operations`, `objective`,
`constraints`, `data_structures`, `algorithm_hints`, `uncertainties`. Skip empty
ones entirely rather than rendering empty headers.

**Done when:** a stranger looking at the screen can tell which details the
system is confident about.

### F3 — Candidates (1.5h) · `CandidateList.tsx`, `ConfidenceScore.tsx`

Cards from `searchCandidates({memory, memory_id})`. Each shows title,
difficulty, confidence bar, `reason`, `topics`, and company provenance:

```
Minimum Path Sum                            91%
medium · Array, Dynamic Programming, Matrix
Asked at Google, Amazon and 39 others
"Grid with down/right moves, minimizing a sum."
```

`companies` is truncated to 5 — use `company_count` for the total. Selecting a
card stores it and advances.

**Done when:** three candidates render with distinguishable confidence and you
can pick one.

### F4 — Reconstruction (2h) · `ProblemDisplay.tsx` ⚠️ **the money screen**

Calls `reconstructProblem({memory_id, candidate_id})`. Renders title,
description, constraints, examples — **each labelled by provenance**:

```ts
type Provenance = 'remembered' | 'retrieved' | 'inferred'
problem.provenance  // { title: 'retrieved', constraints: 'inferred', ... }
```

Three visually distinct treatments. Suggested, but make it yours:

| Value | Meaning | Treatment |
| --- | --- | --- |
| `remembered` | the user said it | solid accent, ✓ |
| `retrieved` | from the corpus | neutral, no marker |
| `inferred` | model supplied it | dashed border, muted, ⚠ + tooltip |

**A key may be absent** — that means the pipeline made no claim. Render
unlabelled; never default to a value.

Also render `problem.notes[]` as caveats ("You weren't sure about obstacles;
this problem has none").

**Done when:** an inferred constraint is unmistakably not something the user
remembered.

### F5 — Editor (1h) · `CodeEditor.tsx`

Monaco, seeded from `problem.starter_code` (fall back to an empty buffer when
`null`). **Python only** — don't build a language switcher.

Monaco loads from a CDN by default; if the venue wifi is unreliable, vendor it.

**Done when:** you can type a solution and it survives step changes.

### F6 — Results (1h) · `TestResults.tsx`

`verifySolution({problem_id, code, language: 'python'})` →

```
✓ Accepted        12 / 12 passed
Runtime 0.21s · Memory 18MB
```

`results[]` carries per-case `input`/`expected_output`/`actual_output` — show
the first failing case, collapsed by default. This is the demo's last beat;
make it land.

### F7 — States and polish (2h)

Every stage needs: loading, empty, and error. The mock layer adds a 400ms delay
specifically so you build these rather than discovering them missing on stage.

Graceful copy beats a stack trace (§20):

> "We couldn't confidently identify the problem. Try adding another detail."

### F8 — Integration (1h)

Set `VITE_USE_MOCK=false`, start the backend, click through. Every response
shape is already identical, so this should be uneventful. If something breaks
it's a contract drift — say so in the group chat rather than patching around it.

---

## Optional, if time allows

* Company filter chip feeding `companies` on `POST /search` — prunes 3,399
  problems to ~2,300 for "it was a Google question," and demos well.
* A browse screen over `listProblems({limit, difficulty, company, search})`.
  The client function and mocks already exist.

---

## Rules

* All HTTP goes through `src/services/api.ts`. No `axios` calls in components.
* No AI logic, no database access, no Judge0, no API keys in this directory.
* Types live in `src/types/index.ts` and mirror `backend/app/schemas/`. If you
  need a shape change, it changes in `docs/API.md`, the backend schema and the
  TS types **together**, and you tell the other two.

## What is already done for you

| Asset | Location |
| --- | --- |
| 7 API functions, mock-switched | `src/services/api.ts` |
| 18 TypeScript interfaces | `src/types/index.ts` |
| 8 realistic mock fixtures | `src/data/mockData.ts` |
| Full request/response contract | `docs/API.md` |
| Tailwind, Vite, Monaco, router | configured |

## Rough budget

F0–F3 ≈ 5h (the flow works end to end on mocks) · F4–F6 ≈ 4h (the payoff
screens) · F7–F8 ≈ 3h. Call it **12 hours** with slack, which fits the
hours 2–18 window in CLAUDE.md §17.
