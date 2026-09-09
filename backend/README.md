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

**Every endpoint is under `/api`** — `/api/problems`, `/api/auth/me`, and so on.
`/health` and `/health/db` are the exceptions, being probes rather than API. The
prefix exists because in deployment one process serves the API *and* the built
frontend from a single origin, where `/problems` is a page as well as an
endpoint. `API_PREFIX` in `app/config.py` is the single definition of it.

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

## Database access

All queries go through [app/db/database.py](app/db/database.py). Never call
`psycopg.connect` anywhere else.

```python
from app.db.database import query, query_one, execute, get_conn

rows = query("SELECT slug, title FROM problems WHERE difficulty = %s", ("medium",))
one  = query_one("SELECT * FROM problems WHERE slug = %s", ("two-sum",))
new  = execute("INSERT INTO problem_memories (raw_transcript) VALUES (%s) RETURNING id", (text,))

with get_conn() as conn, conn.cursor() as cur:   # multi-statement transaction
    cur.execute(...)
    cur.execute(...)
```

Notes:

* Rows are `dict`s (`row["title"]`), so SELECT column order never matters.
* `get_conn()` commits on clean exit and rolls back on any exception.
* Always pass parameters as `%s` placeholders — never f-string SQL.
* pgvector is registered per connection, so `vector` columns adapt to and from
  Python lists. Reads come back as `pgvector.Vector`; call `.to_list()` for a
  plain list. Cosine distance is the `<=>` operator.
* One connection per unit of work, no pool. A local connect is ~5ms; add
  `psycopg_pool` only if that ever shows up in a profile.

Gotchas worth knowing:

* `save_memory` writes all **seven** Genome fields. `data_structures` and
  `algorithm_hints` were added to `problem_memories` after the initial schema —
  if your `POST /memory` silently drops them, your volume predates that change;
  see [../database/README.md](../database/README.md#schema-changes-after-first-boot).
* `get_problem` accepts a UUID **or** a slug. Two separate SQL placeholders are
  used on purpose: reusing one makes Postgres infer `uuid` from the first use,
  and `slug = $1` then fails with `operator does not exist: text = uuid`.
* Filters build parameterised `WHERE` fragments. Never f-string SQL.

`GET /health/db` reports reachability plus corpus size:

```json
{ "status": "ok", "db": "memoize", "problems": 5, "embedded": 0 }
```

It returns 503 with the driver's message when the database is down.

## Mock mode

`USE_MOCK_AI=true` in `.env` makes `ai_service` and `judge_service` return canned
responses, so every endpoint answers with a correctly shaped payload before the
AI modules and Judge0 are wired up. Flip it to `false` as each service lands.

It only covers the **AI and Judge0** calls — the database layer is always real.
So `POST /memory` returns a mocked genome but persists it and hands back a
genuine UUID, and `/problems` is live against Postgres regardless of the flag.

## Endpoints

See [../docs/API.md](../docs/API.md) for the full contract.

**Status** says what the endpoint actually does right now — `live` is real,
`mocked` returns canned data of the correct shape.

Paths are shown without the `/api` prefix that all of them except the two
`/health` probes carry.

| Method | Path | Purpose | Status |
| --- | --- | --- | --- |
| GET | `/health` | liveness | live |
| GET | `/health/db` | DB reachable + corpus size | live |
| GET | `/problems` | browse corpus; `difficulty`/`company`/`topic`/`origin`/`search`/`sort` | live |
| GET | `/problems/facets` | every browse axis with counts, one request | live |
| GET | `/problems/{id}` | one problem, **by UUID or slug** | live |
| POST | `/memory` | transcript → Genome, persisted | **live** when a key is set, else mocked |
| GET | `/memory/{id}` | read back a stored genome | live |
| POST | `/search` | genome → ranked candidates | **live** |
| POST | `/reconstruct` | memory + candidate → full problem | **live** |
| POST | `/contribute/match` | is this problem already in the corpus? | **live** |
| POST | `/contribute` | create a community problem, or corroborate one | **live** |
| GET | `/languages` | supported languages + starter programs | **live** |
| GET | `/progress` | this session's solved/attempted slugs | **live** |
| GET | `/progress/{id}` | this session's standing on one problem | **live** |
| POST | `/verify` | run **or** submit code → Judge0 results | **live** |

`/problems` returns `{total, limit, offset, problems[]}` — `total` is the count
matching the filters, not the page size. `companies` on each row is sliced to 5
for display; `company_count` is the true total.

`/problems/{id}` uses **`ProblemSummary`/`ProblemDetail`, not the `Problem`
shape from `/reconstruct`**. A corpus row is stored text; a reconstructed
problem also carries `constraints`, `examples`, `confidence` and `provenance`,
which Gemini produces at reconstruct time and which are not columns.

`/problems/facets` is registered **before** `/problems/{id}`. FastAPI matches
routes in declaration order, so the other way round `facets` is read as an
identifier and 404s.

Two things about the `companies` array are worth knowing before you touch that
SQL. It is ranked by how much of the corpus each company asks, not stored
order — the column is alphabetical, so slicing it raw put "Accenture, Accolite,
Adobe" on every single row. The ranking comes from a CTE that unnests the whole
corpus per request; at 1,124 rows that is a few milliseconds, and unlike a
hand-written list of "important" companies it stays correct as the corpus grows.

## Contributions

`POST /contribute/match` then `POST /contribute`. Two steps because the
interesting case is the first one: a user describing a problem we already have
should be told so, not silently seeded as a near-duplicate. The match step runs
the ordinary recall pipeline but swallows the 400/404 that mean "nothing found",
since that is the outcome that justifies contributing.

Creating writes an `origin = 'community'` row with `confidence = 0.35` and logs
a `contributions` row. Confidence is
`min(0.95, 0.35 + 0.15 × (contribution_count − 1))` — linear so it can be
explained in one sentence, capped below 1.0 because a remembered statement never
becomes as trustworthy as one fetched from LeetCode. Corpus rows stay at 1.0;
somebody agreeing with LeetCode is not evidence about LeetCode.

The row is inserted with `contribution_count = 0` and `record_contribution()`
brings it to 1. Seeding the counter at 1 as well double-counted the author, so
the *second* person to describe a problem jumped it straight to 0.65.

Two failures refuse rather than half-succeed. An empty drafted statement is a
`422`: a blank description matches everything in vector search. A failed
embedding is a `503` and saves nothing, because a row with no vector exists in
the browse list but is invisible to recall — the most confusing possible
outcome.

## Identity and accounts

`app/identity.py` is the **only** module that knows how a caller is identified.
It answers with a `Principal`, which carries two ids that are not the same kind
of thing:

| | What it is | Trust |
| --- | --- | --- |
| `session_id` | a UUID the browser generates and stores, sent as `X-Session-Id` | none — free to mint, never a credential |
| `user_id` | an account, established by the signed session cookie | this one |

A missing or malformed header, or no cookie, degrades to anonymous rather than
erroring: an unidentified caller can still browse and run code.

**§20b predicted the wrong shape.** The plan was that `current_session()` would
start returning a user id, so "no other file changes". One column holding two id
spaces cannot be foreign-keyed, cannot distinguish an anonymous row from a
user's, and makes claiming a destructive rewrite. So `user_id` sits *beside*
`session_id` in `submissions` and `contributions`, and `problems.created_by`
records who added a community problem — which nothing recorded before, so
"questions I added" was unanswerable regardless of accounts.

`principal.owner` prefers the account: a signed-in user's history is theirs
across every browser they have used, and only a signed-out visitor is scoped to
one browser.

### Claiming

Every sign-in runs `auth_service.claim()`, which fills `user_id` on rows that
have this browser's `session_id` and no owner yet. Not just the first sign-in —
people work signed out on a second machine, and that history has no reason to be
stranded. Only unclaimed rows move, so signing in on a shared browser cannot
take somebody else's attributed work.

### Sessions are rows, not a JWT

The cookie holds a random token; `auth_sessions` stores only its SHA-256. Two
consequences worth the table: reading the database hands nobody a live session,
and **sign-out actually ends the session**. A self-contained JWT cannot be
revoked, so a captured one stays valid until it expires and "sign out" becomes a
lie about the one case it exists for.

### What is deliberately not clever

* **Sign-in failures say one thing.** "No such account" and "wrong password" as
  separate messages is an account-enumeration oracle, and so is a
  forgot-password endpoint that behaves differently for an unknown address.
  Signup is the exception: refusing a duplicate without saying why leaves the
  person retrying forever, and the address is already known to whoever holds it.
* **OAuth links to an existing account only on a provider-verified email.**
  Otherwise anyone who can set an arbitrary address at a provider walks into the
  account that owns it. GitHub is asked for its verified primary address
  explicitly; Google's `email_verified` is checked.
* **Password reset needs no table.** The token is signed and carries the user's
  `password_changed_at`; using it changes the password, which voids every token
  minted before. Single-use without storage. It also revokes every other
  session, because "somebody else may have my account" is what resets are for.
* **Email delivery is a seam.** `EMAIL_PROVIDER=console` prints the link to the
  log, so the whole verify/reset flow works with no provider account and no
  domain — the same idea as `USE_MOCK_AI`. It is loud rather than silent: mail
  that vanishes without trace is how you ship a reset flow that never worked.

### The guest limit

A signed-out visitor may run `GUEST_PROBLEM_LIMIT` (2) **distinct problems**;
iterating on one you have already started is always free. Enforced in `/verify`
because a client cannot be trusted to enforce it, and returned as
`requires_sign_in: true` with `total: 0` rather than an error — the code never
ran, so nothing is wrong with it and the editor shows a prompt, not a failure.

It is a nudge, not a boundary. Clearing site data mints a new session id and
resets the count, and the code says so rather than implying otherwise. Treating
it as real enforcement would be the same mistake as treating a session id as a
credential.

### Run vs submit

`submissions.kind` is `run` or `submit`. Only an accepted **submit** marks a
problem solved — a run that happens to pass is a trial, and completing the
problem on the user's behalf takes the decision away from them.
`problem_progress()` encodes this as
`bool_or(kind = 'submit' AND total > 0 AND passed = total)`, and there are tests
for both halves.

### One contribution per account

`uq_contribution_per_user` is a partial unique index on `(problem_id, user_id)`,
and `uq_contribution_per_session` still covers signed-out traffic. Confidence
measures how many *independent* people described a problem, so without it one
person clicking "that's it" five times walks a problem from 0.35 to 0.95 alone.

The per-session index was never enough — §20b said as much — because a session
id is free to mint. The per-user one is what makes the formula honest. `record_contribution` inserts with
`ON CONFLICT DO NOTHING` and returns `counted: False` when the row was skipped,
so the API can tell the user their account is already on file rather than
pretending it moved the number.

## Multi-language execution

Every supported language lives in `app/languages.py`: our stable id, a label, a
Judge0 id, Monaco's mode, and a starter program.

**Adding one costs a Judge0 id and a starter template.** CLAUDE.md §9 originally
scoped this to Python because "coding problems are function-signature shaped, so
every language needs its own driver that parses stdin, calls the function and
prints the result". That is true for a LeetCode-shaped signature — and it is
exactly what the stdin/stdout decision avoided. A solution here is a whole
program that reads stdin and prints an answer, so **the same stored test cases
run unchanged against all eleven languages.**

Two things that bite:

* Judge0 compiles Java as `Main.java`, so the starter must declare
  `public class Main`. There is a test for it.
* Judge0 ids are pinned to specific compiler versions on CE, so they are
  recorded in the registry rather than looked up at runtime.

## Code execution (Judge0)

Setup options and API gotchas: **[../docs/JUDGE0.md](../docs/JUDGE0.md)**.

`POST /verify` runs real code. Flow:

```
/verify -> resolve problem (uuid or slug) -> load <=5 test cases
        -> POST /submissions/batch  (one request, all cases)
        -> poll GET /submissions/batch until every status.id > 2
        -> compare stdout to expected_output, rstrip'd
        -> save to `submissions` -> VerifyResponse
```

Notes from the live API, worth knowing before you change anything:

* `time` is a **string** in seconds (`"0.011"`); `memory` is an **int in KB**.
* `stdout` always has a trailing newline — hence `rstrip()` on both sides.
* The batch endpoint returns **201**, and does **not** support `wait=true`;
  it must be polled. Status ids 1 and 2 are queued/processing.
* Judge0 reports `Accepted` when the program merely *ran*. We never send it an
  `expected_output`, so correctness is decided here — a run can be `Accepted`
  by Judge0 and still be `Wrong Answer` to us.
* On failure, `actual_output` falls back to stderr/compile output so the UI can
  show why.
* Python only (`LANGUAGE_IDS`). Other languages return a message, not an error.
* Network failure degrades to a `Judge0 unavailable: ...` status, never a 500.

## How a solution is run

Two modes. Judge0 sees the same thing either way — stdin in, stdout out. What
differs is **who writes the parsing**.

### functional (the default for corpus problems)

You write the function the statement describes:

```python
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
```

`app.harness` appends a driver that reads one JSON argument per line,
deserialises each by its declared type, calls the method and prints what it
returns. Answers are compared **as JSON values**, so `[0,1]` and `[0, 1]` are
the same answer, and `problems.judge_mode` handles the statements that say the
order is free.

Types come from LeetCode's own `metaData`, so signatures are fetched, not
guessed — including `ListNode` and `TreeNode`, which the harness builds from the
array form the statements use. A `void` problem mutates its first argument, and
that mutation is printed as the answer.

### stdin (the original contract)

`test_cases.input` goes to stdin verbatim; stdout is compared after stripping
trailing whitespace. Class-design problems (LRU Cache, Min Stack — there is no
single function to call) and anything the harness has no type for stay here, and
`problems.io_format` states the format for them.

### Why not generate a parser per problem

The alternative was a stdin-parsing preamble generated per problem per language.
That is problems x languages — about 37,000 artifacts, each independently able
to be subtly wrong — against 11 harnesses written once and tested. A parser that
is subtly wrong tells a correct solution it is wrong, the failure this codebase
already treats as worse than having no tests.

The trade is real, though: stdin/stdout is what made eleven languages nearly
free, and functional mode costs one harness per language. **Four exist —
Python, Java, C++ and C** — covering 986 of 987 functional problems. The other
seven languages still run every stdin problem. `GET /problems/{id}` returns
`runnable_languages` and the editor offers only those, because a language that
answers "not available yet" the moment you press Run is worse than one absent.

Each harness solves the same problem differently:

| | How arguments are typed |
| --- | --- |
| Python | JSON maps 1:1 onto Python values; almost nothing to convert |
| Java | **reflection** — `getGenericParameterTypes()` reports what the method really declares, `List<List<Integer>>` included, so one recursive converter covers every problem |
| C++ | no reflection, so the call site is generated from `metaData` against a fixed library of `from()` / `ser()` overloads |
| C | no containers either: `int[] nums` expands to `(int* nums, int numsSize)` and array returns come back through `int* returnSize` |

None of the three has a JSON parser available — Java's is not in the standard
library and Judge0 ships no jars, and C/C++ get a bare toolchain — so each
carries a small hand-written one.

**C's calling convention is not documented anywhere.** It was derived from the
starters and then checked against every C starter in the corpus: 510 matched, 9
did not, and all nine turned out to be problems whose `metaData` does not
describe the real function (`hasCycle` lists a `pos` argument that exists in no
language). Those are refused at load time, not worked around in the harness.

Two things that cost a debugging round each, worth not rediscovering: Judge0
compiles Java as `Main.java`, so the entry class must be `Main` and `Solution`
must not be public; and Judge0 links C **without `-lm`**, so `llround` fails at
link time and the harness rounds by hand.

### What only running it catches

Every functional problem *builds* in all four languages, which turned out to
mean very little. Four defects survived that check and were found only by
executing real solutions against real stored cases, one problem per rare type:

* **A pasted `import` did not compile in Java.** The preamble declares
  `ListNode`/`TreeNode` above the person's code, and Java wants every import
  before the first type declaration — so `import java.util.*;` landed mid-file.
  Anything using a `HashMap` failed, with an error pointing at a line the person
  did not write. Imports are hoisted now.
* **Java could not serialise a tree with a missing child.** The level-order BFS
  pushes nulls deliberately, because a null is how a gap is written, and
  `ArrayDeque` rejects null elements. Every `TreeNode` return threw. It is a
  `LinkedList` now.
* **`ListNode[]` built one chain, not several.** Python collapsed the type to
  its element name, losing the nesting depth, so every input row was
  concatenated into a single linked list.
* **An empty result printed `null`, not `[]`.** Returning `None` for "no nodes"
  is what a correct solution does; the expected outputs write it as `[]`.

The lesson worth keeping: the harness surface is **21 atomic types**, not 509
problems, and the rare end of that distribution — `double[]`, `character[]`,
`ListNode[]`, `list<boolean>` appear once or twice each — is where every one of
these hid. `tests/test_harness.py` pins each.

### What is left in stdin mode

137 of 1,125 problems have no test cases — a statement you can read but not
run — and one more (the community-contributed problem) runs on stdin with a
stated `io_format`. The breakdown is in
[ai/corpus/README.md](../ai/corpus/README.md); the short version is that 53 are
class-design problems, 44 are SQL, and only about 18 are recoverable at all.

Four more are functional but offer three languages instead of four, because C
has no way to express their argument types: `construct-quad-tree`,
`employee-importance`, `find-duplicate-subtrees` and
`flatten-a-multilevel-doubly-linked-list`. They are solvable, just not in C.

**Some problems are not solvable here at all, and say so.** SQL questions and
class-design ones are identified by LeetCode's own `Database` and `Design` topic
tags, so it is not our inference. `GET /problems/{id}` returns `solvable: false`
with a one-sentence reason and the UI links out. `POST /verify` refuses them
before the generate-on-first-run path: generating stdin cases for a problem that
has no stdin format would invent one and then judge somebody against it.

The gate has to sit on `/reconstruct` too, not just `/verify`. A reconstruction
stores its worked examples as test cases — normally a free win, since the problem
becomes runnable for everyone afterwards. For a SQL or class-design problem those
examples are invented, and storing them made the problem look runnable to every
later check: `solvable` reads `test_case_count`, so one recall was enough to
reopen the editor on a problem that can never be graded. `ai_service.reconstruct`
judges the corpus row before saving anything.

**A functional problem must offer at least one language we can run.** LeetCode's
JavaScript-track problems ship starters only for JS and TS, which have no
harness, so converting one produced a problem the editor offered zero languages
for — browsable, unsolvable, and silent about why. `load_signatures` refuses
those now, and reverted the one that had slipped through.

### Known limitation: problems with more than one right answer

Comparison is by value, and `judge_mode` can loosen it to `unordered` or `set`,
but nothing expresses "any valid BST". Three problems are consequently
unpassable — `convert-sorted-array-to-binary-search-tree`,
`convert-sorted-list-to-binary-search-tree` and `delete-node-in-a-bst` —
because a correct answer that differs from the stored one is judged wrong.
LeetCode runs a special judge per problem here; we do not. They are left as-is
rather than quietly loosened, because a judge that accepts a wrong answer is a
worse failure than one that rejects a right one.

## Test cases

Two sources, in order of trust.

**1. Reconstruction examples (primary).** `/reconstruct` stores its own examples
as test cases. They are already stdin/stdout, already shown to the user, and
cost **no extra model request** — the reconstruction prompt pins the format, so
they cannot drift from what is on screen.

**2. Cold generation (fallback).** When `/verify` finds a problem with no cases
— one the user never reconstructed — it generates them, then **validates them by
execution**:

```
generate_suite()  -> reference_solution + N candidate cases
judge_service.run_reference(solution, inputs)  -> what the code actually prints
keep only cases where actual == claimed        -> store those
```

Asking for answers alone does not work. Measured on `two-sum`, one case put the
target first, another put it last, and a third was wrong under either reading —
a correct solution would have failed whichever convention it picked. Requiring a
reference solution fixes the format (the model has to write a parser) and
running it catches the arithmetic: 4 of 5 cases kept, the wrong one dropped.

Generation happens **once per problem ever** — `save_test_cases` is
**first-writer-wins**, and the next visit reads the rows back.

If every case fails validation the endpoint reports `No test cases for this
problem` rather than storing something untrustworthy. A wrong expected output is
worse than none: it tells someone their correct solution is broken.

### The input format is part of the problem

Upstream statements are written for a function signature — "given an array
`nums` and an integer `target`" — and never say which line the target is on.
Here a solution is a whole program reading stdin, so that is the difference
between a correct answer and a parse error. `problems.io_format` states it, in
prose, and `/problems/{id}` and `/reconstruct` return it for the UI to render
above the constraints.

It is **write-once**. `set_io_format` will not overwrite a stated format, and
`save_test_cases` will not add cases to a problem that already has some. Both
enforce the same rule:

> Test cases are trustworthy as a **set**, not individually. They do not
> compose.

This was a real bug, not a hypothetical. Storage used to merge on
`(problem_id, input)`, so every reconstruction appended its own examples. Two
formats for `two-sum` accumulated — `n nums… target` as whitespace-separated
tokens, and `target` then `nums` — and no program could pass more than six of
the nine stored cases. Regression tests:
`test_test_cases_do_not_accumulate_across_formats` and
`test_io_format_is_stored_and_never_silently_rewritten`.

To audit what is already stored, see `ai/corpus/repair_test_cases.py`. It
arbitrates by execution rather than by inspecting the strings — a structural
signature cannot tell `minimum-path-sum`'s legitimately varying line counts from
`two-sum`'s corruption, but "does one program pass them all" can.

## Error handling

Handlers live in [app/errors.py](app/errors.py), registered most-specific-first.
Nothing escapes as a bare 500, and every response carries an actionable `hint`.

| Failure | Status | Response |
| --- | --- | --- |
| Postgres unreachable | 503 | "Database unavailable." + `docker compose up -d` |
| Other `psycopg.Error` | 500 | names the type; points at a stale volume for a missing column |
| Judge0 / Gemini failure | 502 | suggests `USE_MOCK_AI=true` |
| `NotImplementedError` | 501 | "not implemented yet" + how to fall back to mocks |
| Anything else | 500 | logged with traceback; the client gets a message, never internals |

**Startup guard:** `USE_MOCK_AI=false` with no `GEMINI_API_KEY` refuses to boot
rather than failing on the first request mid-demo. `.env.example` placeholders
(`your_..._here`) count as unset, so a copied-but-unedited `.env` is caught.

`GET /health` reports both flags:

```json
{ "status": "ok", "mock_ai": true, "ai_ready": false }
```

## Deployment

Full runbook: [../docs/DEPLOY.md](../docs/DEPLOY.md). What the backend
contributes to it:

**It serves the frontend.** If `frontend/dist` exists (or `FRONTEND_DIST` points
somewhere that does), `main.py` mounts it last, behind every API route, with
unmatched HTML navigations falling back to `index.html` so a deep link like
`/problems/two-sum` reaches React Router. Locally the directory does not exist
and nothing changes — Vite still serves the app on 5173.

This is a cookie decision rather than a packaging one. `onrender.com` is on the
Public Suffix List, so `app.onrender.com` and `api.onrender.com` are different
*sites* and a `SameSite=Lax` cookie is not sent between them: sign-in would
return 200, set the cookie, and every request afterwards would arrive signed
out. `COOKIE_SAMESITE=none` avoids that at the price of a third-party cookie,
which Safari blocks. One origin makes Lax correct and CORS unnecessary.

`auth_warnings()` catches the mistake at boot — it compares the *sites* of
`PUBLIC_APP_URL` and `PUBLIC_API_URL`, treating the multi-label public suffixes
the free tiers hand out (`onrender.com`, `vercel.app`, …) as the sites they are.

**Two URLs come from the platform.** `PUBLIC_APP_URL` and `PUBLIC_API_URL`
default to `RENDER_EXTERNAL_URL` when it is set, so the single-origin deployment
needs neither. `COOKIE_SECURE` is then derived from that URL being https.

**The database is external.** Render's free Postgres expires 30 days after
creation and the corpus is the product, so `DATABASE_URL` points at Neon, whose
free tier carries pgvector. Neon has no `docker-entrypoint-initdb.d`, so
`database/init/*.sql` is applied by hand once — see the runbook.

**The image is the contract.** `Dockerfile` at the repo root builds the frontend
with Node and runs it with Python, keeping `backend/` and `ai/` siblings because
`app/__init__.py` puts the repo root on `sys.path`. Build and run it locally
before deploying; it catches the single-origin wiring without a push.

## Tests

```bash
cd backend && ../venv/bin/python -m pytest tests -q
```

25 integration tests. They need Postgres (`docker compose up -d`) but **never**
call Gemini or Judge0 — both are monkeypatched, so the suite is fast, free and
runs without an API key.

What they cover: response shapes, every filter, pagination, UUID-or-slug lookup,
404-not-500 on malformed ids, the seven-field genome round-trip, the real
extraction path with Gemini stubbed, the no-key fallback, and Judge0 degrading
instead of crashing.

They earn their keep: the first run caught `ModuleNotFoundError: ai` — uvicorn
starts from `backend/`, so `import ai.*` did not resolve. `app/__init__.py` now
puts the repo root on `sys.path`. That would otherwise have surfaced the moment
someone added a real key.

### Status

The whole pipeline is wired: `/memory`, `/search`, `/reconstruct`, `/verify` and
both `/contribute` endpoints call the real AI and database paths. Set
`GEMINI_API_KEY` and `USE_MOCK_AI=false`. With no key the AI endpoints fall back
to correctly shaped mocks rather than failing, so a teammate without one can
still run the frontend — except `POST /contribute` (create), which returns a
`503` explaining why, since fabricating a corpus row from a mock would be worse
than refusing.

Done: B1 connection helper · B2 schema split · B3–B4 corpus browse ·
B5 memory persistence · B6 test cases + submissions · B7–B8 Judge0 ·
B9 error handling · B10 AI wiring · B11 facets + browse filters ·
B12 contributions.

### Known gap

`test_cases` rows carry no record of the format they were generated in.
Validation proves each case is internally consistent — a reference solution was
executed against it — but nothing stops two batches generated at different times
from using different stdin shapes for the same problem. `Two Sum` accumulated
three. Storing the reference solution alongside its cases would fix it
properly.
