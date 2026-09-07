# Memoize

Reconstruct the coding problem you can't quite remember.

You describe a half-remembered problem ("there was a grid, you could only move
right or down, and you had to minimize something"). Memoize extracts what you
actually remember, searches a corpus of known problems, reranks the matches,
rebuilds the full statement, and then lets you solve and verify it in the browser.

Around that sits an ordinary problem site — 1,124 problems browsable by company,
topic and difficulty, each one openable in a full-screen editor — plus a
contribution flow for the problems we do not have. All three share one corpus:
browsing is how you find a problem you can name, recall is how you find one you
cannot, and contributing is what happens when neither works.

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
| AI / RAG | Gemini 3.1 Flash Lite + `gemini-embedding-001` | Native `response_schema` output; disk-cached |
| Database | PostgreSQL 16 + pgvector (Docker) | Exact vector scan, no ANN index |
| Execution | Judge0 API | Functional or stdin, batch endpoint, 5 test cases |

### Why these narrowings

Each one removes hours of work without removing anything the demo shows.

- **stdin/stdout as transport, not as the interface.** Judge0 only speaks
  stdin/stdout, so that is how it is driven. But the statements are written for a
  function signature, so on most problems a harness deserialises the arguments,
  calls your method and serialises what it returns. Problems with no function to
  call — LRU Cache, Min Stack — keep the plain stdin contract and state their
  input format.
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
memoize/
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
git clone <repo-url> memoize
cd memoize
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
| `GEMINI_TEXT_MODEL` | Default `gemini-3.1-flash-lite` — chosen for free-tier headroom; `gemini-3.6-flash` caps at 20 requests/day |
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
| GET | `/problems/facets` | company / topic / difficulty counts for the browse nav |
| POST | `/contribute/match` | do we already have this problem? |
| POST | `/contribute` | add a community problem, or corroborate one |
| GET | `/languages` | supported languages + their starter programs |
| GET | `/progress`, `/progress/{id}` | what this session has solved and attempted |
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

## Screens

| Route | What it is |
| --- | --- |
| `/` | Home. Search, the three ways in, then companies, topics and the most-asked list. |
| `/problems` | The bank as a filterable table. Every filter lives in the URL. |
| `/companies`, `/topics` | Directories that feed straight back into `/problems`. |
| `/problems/:slug` | One problem: statement, metadata, way into the editor. |
| `/recall` | The four-step vague-memory flow. |
| `/contribute` | Describe a missing problem; match first, create second. |
| `/solve/:slug` | Full-screen IDE: statement, Monaco, 11 languages, run/submit, elapsed timer. |

The home page deliberately does **not** lead with recall. Recall is the
strongest differentiator but it is not why most people arrive — they arrive for
"what does company X ask". Leading with the recall box sold one feature and hid
the bank, so the order is now search → the three ways in → companies → topics →
problems, with recall as the third and most prominent way in.

`/solve` renders outside the site shell on purpose. Once you are writing code
the navigation is a distraction, and the only bright thing on the display should
be the code.

### Solving

Most problems are solved the way the statement describes them — you write the
method, and the arguments arrive as the examples show them:

```python
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
```

Answers are compared as values, not text, so `[0,1]` and `[0, 1]` are the same
answer, and problems whose statements say the order is free are judged that way.

These run in **Python, Java, C++ and C**, each with its own harness converting
the arguments to that language's types — `vector<int>` in C++, `int[]` in Java,
and in C the `(int* nums, int numsSize)` pair LeetCode's own starters declare.

Problems with no single function to call keep the stdin contract, where a
solution is a whole program and the input format is stated on the problem. Those
run in all eleven languages — Python, C++, Java, JavaScript, C, Go, C#, Kotlin,
Ruby, Rust, TypeScript — from the same stored test cases.

The editor only ever lists what a problem can actually run.

**Run** is a trial; **Submit** is the claim that you are done, and only an
accepted submit marks a problem complete. Submit stays disabled until a run has
passed, and goes back to disabled the moment the code changes — the passing run
described the old code.

Progress (solved, attempted, run counts) is attributed to an `X-Session-Id` the
browser generates and keeps. There are no accounts yet, so it identifies a
browser rather than a person; `backend/app/identity.py` is the single seam that
becomes a user id when auth lands.

---

### Design system

The whole site is the code editor's chrome. It is dark, and the ramp is anchored
on the brand's own dark end — `shadowGrey` and `prussianBlue` were always the
bottom of that palette, so they became surfaces rather than being replaced.

| Token | | Job |
| --- | --- | --- |
| `ground` | `#101219` | the page, and the Monaco background |
| `panel` | `#171A24` | cards, tables, the hero band |
| `raised` | `#1E212B` | shadowGrey — inputs, hover, chips |
| `select` | `#191D32` | prussianBlue — selected row, active filter |
| `line` / `lineStrong` | `#262A36` / `#343947` | hairlines |
| `ink` / `ink2` / `ink3` | `#E6E8EF` / `#A2A8BC` / `#858CA2` | text |

**Colour carries meaning, and each one means one thing.** `accent` (amberEarth,
`#E98A15`) is the action and the thing running right now — the Run button, the
submit, the active tab, the cursor. Nothing else. Links are `link` blue.
Uncertainty and community confidence are `medium` yellow, deliberately *not*
amber, so a caveat never competes with a button.

Difficulty and pass/fail borrow an editor's token colours — `easy` is the same
green as a string literal, `hard` the same red as an error — and
`src/lib/monacoTheme.ts` paints Monaco in exactly those values, so a keyword and
an "Easy" tag are literally the same colour. That is why the editor reads as
part of the page rather than a window pasted onto it.

IBM Plex Mono is the interface chrome (nav, buttons, labels, counts, table
heads, metadata); IBM Plex Sans carries prose. One named type scale — `micro
tiny small base lede h3 h2 h1 display` — and one component vocabulary in
`src/index.css` (`.shell .band .label .btn-* .card .chip .field .th .td`). Use
those rather than Tailwind's default sizes or raw hexes, or screens stop
matching each other. Rules, never shadows; square corners; one loud element per
screen.

`ink3` sits at `#858CA2` rather than something dimmer because it carries the
11px labels — the smallest text on the site — and anything darker fell under
4.5:1 on a raised panel.

---

## Scope

36-hour hackathon MVP. No auth, no microservices, no Kubernetes, no ORM, no
migrations, no vector index, no deployment, no custom sandbox. Working
end-to-end flow beats architectural polish.

---

## Running it

Three processes, in this order. Each block is a separate terminal; the database
one exits immediately, so two terminals stay open.

```bash
# 1. Database — detached, stays up across restarts
docker compose up -d
docker compose logs -f db          # first boot only: watch the init scripts land

# 2. Backend + AI — one venv covers both
source venv/bin/activate 
cd backend && uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm run dev
```

| Service | URL |
| --- | --- |
| App | http://localhost:5173 |
| API docs (live schema) | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Postgres | `localhost:5432`, db/user/password `recollect` |

### Check it before demoing

Two probes, and between them they tell you which layers are actually live.

```bash
curl -s localhost:8000/health    | python -m json.tool
curl -s localhost:8000/health/db | python -m json.tool
```

```json
{ "status": "ok", "mock_ai": false, "ai_ready": true }
{ "status": "ok", "db": "recollect", "problems": 1124, "embedded": 1124 }
```

`ai_ready: false` means `GEMINI_API_KEY` is missing or still the placeholder from
`.env.example`. This is worth checking explicitly: the backend degrades to canned
responses rather than erroring, so a dead key looks like a working demo until
someone reads the output. `mock_ai: true` is the same story, deliberately.

`embedded` is the number that decides whether retrieval works at all. If it is 0
while `problems` is not, the corpus loaded but never got embeddings, and every
search will return noise. `/health/db` returns 503 if Docker isn't up.

Then walk one problem end to end — recall, genome, candidates, reconstruct, run.
The first `/verify` on a problem is slower: it has no test cases yet and stops to
generate them (see below).

### Test cases

A problem gets its test cases from one of two places, and neither needs a
manual step:

1. **Reconstruction examples.** `/reconstruct` stores the examples it produced.
   Free — no extra model call — and guaranteed to match what's on screen.
2. **Generated on first verify.** If a problem still has none, `/verify` asks the
   model for a reference solution plus candidate cases, executes that solution on
   Judge0, and keeps only the cases whose real output matches the claimed one.
   Wrong cases are dropped rather than stored.

Both write to `test_cases`, so this happens once per problem. A second run on the
same problem reuses the stored rows. Details and the measured evidence:
[backend/README.md](backend/README.md).

### Running the tests

```bash
source venv/bin/activate
cd backend && pytest -q          # 25 tests, no network, no database required
```

### Stopping

```bash
# Ctrl-C the uvicorn and vite terminals, then:
docker compose down              # keeps the pgdata volume
docker compose down -v           # wipes it — next `up` re-runs database/init/*.sql
```

`down -v` is how you reload a changed schema or a new `03_corpus.sql`: the init
scripts run **only on an empty volume**, so editing them without `-v` does
nothing.

### When something is wrong

| Symptom | Cause |
| --- | --- |
| Candidates are empty or nonsense | Corpus not embedded — check `embedded` on `/health/db` |
| `ModuleNotFoundError: ai` | Backend started from the repo root; run uvicorn from `backend/` |
| Port 8000 in use | An orphaned uvicorn — `ss -ltnp \| grep 8000`, then kill by PID |
| Schema edits have no effect | Init scripts only run on an empty volume; `docker compose down -v` |
| Everything 502s on verify | Judge0 CE is down. `USE_MOCK_AI=true` keeps the flow demoable |

## Attribution

Curated question statements, function signatures and worked examples are sourced
from [LeetCode](https://leetcode.com) via their public GraphQL endpoint, and
remain the property of their respective owners. Memoize is not affiliated with
or endorsed by LeetCode. This is stated in the site footer as well as here.

Community-contributed questions are written by people using the site. They are
labelled `community` throughout, carry a confidence score, and are never mixed
with curated rows without that label.

The company-frequency data in `data/leetcode-companywise-interview-questions/`
is a publicly published dataset of interview question frequencies.
