# Deploying Memoize

The whole thing runs on free tiers. This is the runbook and, more usefully, the
two decisions that are not free to get wrong.

## Shape

```text
                 ┌──────────────────────────────┐
   browser ────► │  Render web service (free)   │
                 │  FastAPI + the built bundle  │
                 └───────┬──────────────┬───────┘
                         │              │
                 ┌───────▼──────┐  ┌────▼────────┐
                 │ Neon         │  │ Judge0 CE   │
                 │ Postgres 16  │  │ + Gemini    │
                 │ + pgvector   │  └─────────────┘
                 └──────────────┘
```

One service, not two. An external database, not Render's.

## Why one origin

`onrender.com` is on the [Public Suffix List][psl]. That makes
`memoize-app.onrender.com` and `memoize-api.onrender.com` different **sites**,
not just different origins — so a `SameSite=Lax` cookie is not sent between
them. Split across two services, sign-in returns 200, sets the cookie, and then
every subsequent request arrives signed out. It looks like a bug in the auth
code and it is not.

`COOKIE_SAMESITE=none` makes the cookie cross-site, and also makes it a
third-party cookie, which Safari blocks by default and Chrome is narrowing. So
the fix is to remove the split: FastAPI serves `frontend/dist` (see
`SERVE_FRONTEND` in `backend/app/config.py`), which also removes CORS and halves
the number of services.

A custom domain works too — `app.you.com` and `api.you.com` share the
registrable domain `you.com` and are same-site. `auth_warnings()` knows the
difference and logs at boot when the two URLs are cross-site with Lax set.

[psl]: https://publicsuffix.org/list/

## Why not Render's Postgres

Render's free Postgres **expires 30 days after creation** (then a grace period,
then deletion). Here the database is not a cache — it is the corpus, the
embeddings, the accounts and everyone's progress.

Neon's free tier does not expire and carries pgvector on every plan, which is
non-negotiable: `ORDER BY embedding <=> %s` is the whole retrieval story. The
corpus is ~21MB, so storage limits are not close to binding.

## Steps

### 1. The database

**Create the project.** neon.tech → sign in with GitHub → **Create project**.
Three choices matter:

| Field | Value | Why |
| --- | --- | --- |
| Postgres version | **16** | Matches `pgvector/pgvector:pg16` locally |
| Region | nearest your Render region (`singapore` in `render.yaml`) | Every query crosses this link |
| Database name | `neondb` is fine | Nothing in the code names it |

Neon gives you one project on the free tier, with a `main` branch. That is the
database. Nothing needs enabling for pgvector — it is available on every plan,
and `01_schema.sql` already does `CREATE EXTENSION IF NOT EXISTS vector`.

**Or link it with the CLI**, which is how this repo is actually wired:

```bash
npm i -g neon@latest && neon login
neon link --project-id <project-id> --branch <branch>
```

That writes `.neon` (gitignored — it names the project, not a secret) and pulls
`DATABASE_URL`, `DATABASE_URL_UNPOOLED` and `NEON_BRANCH` into `.env`, preserving
every other line. `neon.ts` is the config-as-code policy; `neon config plan`
previews a reconcile and `neon deploy` applies one. None of that loads the
schema — that is still the step below.

Note that `env pull` **owns** those three keys and rewrites them on every pull,
so editing them by hand does not survive. That is why `config.py` prefers
`DATABASE_URL_UNPOOLED` rather than expecting you to paste the right one in.

**Take the direct connection string, not the pooled one.** Neon's dashboard
offers both; the pooled host has `-pooler` in it. This app opens one connection
per request and closes it (`app/db/database.py`, deliberately no pool), so there
is nothing for a pooler to amortise — and psycopg 3 prepares statements after a
few executions, which is exactly what transaction-mode poolers are historically
awkward about. Take the plain one:

```text
postgresql://neondb_owner:...@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

Keep `sslmode=require`. psycopg does not add it, and Neon refuses without it.

**Load the schema.** Neon has no `docker-entrypoint-initdb.d`, so the init files
run by hand, once, in order. You do not need psql installed — the local database
container has it, and already mounts `database/init` read-only:

```bash
export NEON_URL='postgresql://neondb_owner:...@ep-xxx.neon.tech/neondb?sslmode=require'

docker exec memoize-db sh -c '
  for f in /docker-entrypoint-initdb.d/*.sql; do
    echo "-- $f"
    psql "$0" -v ON_ERROR_STOP=1 -f "$f" || exit 1
  done' "$NEON_URL"
```

The glob is the point: it sorts lexically, which is the order the numbers encode,
and it picks up a file you add later without anyone remembering to.

Order is not cosmetic: the later files `ALTER TABLE` what the earlier ones
create. `ON_ERROR_STOP=1` matters for the same reason — without it psql reports
a failure and carries on, and you find out three files later.

`03_corpus.sql` is 14MB of INSERTs with a 768-dimension vector on each row.
Locally it takes seconds; over the wire to Neon expect a few minutes. Then check
it actually landed, rather than assuming:

```bash
docker exec memoize-db psql "$NEON_URL" -c \
  'SELECT count(*) AS problems, count(embedding) AS embedded FROM problems;'
```

Both numbers should match what `/health/db` reports locally. A row without an
embedding browses fine and is invisible to recall, which is the most confusing
possible outcome — so it is worth the one query.

**Then point the app at it**, either as `DATABASE_URL` in Render (step 2) or
locally for a smoke test:

```bash
cd backend && DATABASE_URL="$NEON_URL" ../venv/bin/python -m pytest -q
```

That runs the whole suite against Neon and is the cheapest proof the migration
worked.

### 2. The service

Push the repo, then in Render: **New → Blueprint**, point it at this repo. It
reads `render.yaml` and creates one Docker web service. Fill in the variables
marked `sync: false` in the dashboard:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | the Neon string, with `sslmode=require` |
| `GEMINI_API_KEY` | from aistudio.google.com |
| `JUDGE0_API_KEY` / `JUDGE0_API_HOST` | only if using RapidAPI rather than the public CE instance |

`AUTH_SECRET` is generated by Render. `PUBLIC_APP_URL` and `PUBLIC_API_URL` are
left unset on purpose — with one origin they are both `RENDER_EXTERNAL_URL`,
which Render injects.

### 3. Check what the boot log says

`auth_warnings()` prints every setting that is fine locally and wrong in
production. Read them; they are the deployment checklist. A clean production
boot still logs the email one until step 5.

### 4. OAuth (optional)

Both are free to register. The callback URL must match byte for byte:

* GitHub → Settings → Developer settings → OAuth Apps →
  `https://<service>.onrender.com/api/auth/github/callback`
* Google → console.cloud.google.com → Credentials → OAuth client ID (Web) →
  `https://<service>.onrender.com/api/auth/google/callback`

Set the four client id/secret variables. With none set, the app offers email and
password only, which is a supported state rather than a broken one.

### 5. Email

`EMAIL_PROVIDER=console` prints verification and reset links to the service log.
That is genuinely usable while the site is you and a few testers, and it is
honest: nothing pretends to have been delivered.

To actually send, you need a **From address you control** — and on Render free,
you need it over HTTPS.

> **Render free instances block outbound traffic to ports 25, 465 and 587.**
> Any SMTP provider is therefore unreachable from a free web service, and the
> failure is a timeout rather than an error — mail silently stops. This is why
> `EMAIL_PROVIDER=brevo` exists alongside `smtp`: same Brevo account, same free
> allowance, different road. `auth_warnings()` catches `smtp` on Render at boot.

* **Brevo** free (300/day, no expiry) — verifies a *single sender address*, so
  it works before you own a domain. Set `EMAIL_PROVIDER=brevo`, `BREVO_API_KEY`
  (Brevo → SMTP & API → API keys — the **API** key, not the SMTP key), and
  `EMAIL_FROM` to the address you verified. This is the one to deploy with.
* **Resend** free (3,000/month) — but `onboarding@resend.dev` only delivers to
  your own verified address, so real users need a domain you have verified.
  Set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, `EMAIL_FROM`.
* **SMTP** (`EMAIL_PROVIDER=smtp`) is right on a laptop and on hosts that permit
  those ports. Brevo's relay is `smtp-relay.brevo.com:587` with STARTTLS; the
  username is your Brevo login and the password is an **SMTP key**, not your
  account password.

**A note on the sender address.** Brevo will let you verify a Gmail address, and
it works — but mail *from* `@gmail.com` sent through Brevo's servers fails
Gmail's own DMARC alignment, so it tends to land in spam. Fine for testing the
flow, not fine for real users. A domain is the real fix, and it is the same fix
as the OAuth authorized-domain problem below.

## What free actually costs you

* **Cold starts.** The service sleeps after 15 minutes idle and takes about a
  minute to wake. Fine in use, bad thirty seconds before a demo — open it first.
  The free allowance (750 instance-hours against a ~730-hour month) covers one
  service running continuously, which is the other reason not to run two.
* **Sessions survive it.** They are Postgres rows, not process memory, so a
  spin-down does not sign anybody out.
* **Neon's compute suspends too**, after about five minutes idle, and wakes on
  the next connection. That wake lands inside `DB_CONNECT_TIMEOUT`, which
  defaults to 5 seconds — generous for a warm database and not obviously
  generous for a cold one. If the first request after a quiet spell fails with a
  connect timeout and the second succeeds, that is what happened; raise it.
* **Judge0's public CE instance is rate-limited and sometimes down.** It is the
  most likely thing to break, exactly as it is locally. `USE_MOCK_AI=true` is
  still the fallback.

## Running the production image locally

Worth doing once — it catches the single-origin wiring without a deploy:

```bash
docker build -t memoize .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql://recollect:recollect@host.docker.internal:5432/recollect" \
  -e USE_MOCK_AI=true \
  memoize
```

Then open <http://localhost:8000> — the app, the API and the cookie all on one
origin, which is what production is.
