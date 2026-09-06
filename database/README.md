# Database

PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector), run locally via Docker Compose.

## Start / stop

```bash
docker compose up -d      # from the repo root
docker compose logs -f db
docker compose down       # stop, keep data
docker compose down -v    # stop and DELETE the volume
```

## Files

| File | Purpose |
| --- | --- |
| `init/01_schema.sql` | Tables, indexes, `vector` extension |
| `init/03_corpus.sql` | The real embedded corpus — generated, committed (~12 MB) |
| `init/04_seed_testcases.sql` | A few test cases so `/verify` is demoable |

**Filename order matters.** Docker runs these alphabetically, and
`04_seed_testcases.sql` references corpus problems by slug, so it must run after
`03_corpus.sql`. It used to be `02_seed.sql` and inserted its own problem rows —
those shadowed the real corpus entries through `ON CONFLICT (slug) DO NOTHING`,
leaving five popular problems with no embedding and invisible to search.

`03_corpus.sql` is produced by `python -m ai.corpus.load_corpus --dump` and is
**not** hand-edited. If it is missing from your clone, run the pipeline in
[ai/corpus/README.md](../ai/corpus/README.md).

## The `problems` table

Beyond the obvious columns it carries corpus metadata from
`data/leetcode-companywise-interview-questions/`:

| Column | Meaning |
| --- | --- |
| `slug` | LeetCode URL slug — the unique key every loader upserts on |
| `topics` | LeetCode `topicTags`, e.g. `{Array,"Hash Table"}` |
| `companies` | Lowercase company slugs that asked it |
| `company_count` | How many — 126 for Two Sum |
| `popularity` | Summed per-company `Frequency %`; the corpus ranking score |
| `acceptance` | LeetCode acceptance rate, % |
| `recency` | Most recent bucket it appeared in: `30d`/`3mo`/`6mo`/`older` |
| `description_source` | `leetcode` (scraped) or `gemini` (gap-filled) |

`companies` is GIN-indexed, so `WHERE companies @> ARRAY['google']` is cheap.

Scripts in `init/` run **only when the `pgdata` volume is empty**. After editing
them, re-run with `docker compose down -v && docker compose up -d`, or apply the
change by hand:

```bash
docker compose exec -T db psql -U memoize -d memoize < database/init/01_schema.sql
```

## Connecting

```bash
docker compose exec db psql -U memoize -d memoize
```

`DATABASE_URL=postgresql://recollect:recollect@localhost:5432/recollect`

## Schema changes after first boot

`init/*.sql` runs **only on an empty volume**, so editing it does nothing to a
database that already exists. Apply the change by hand as well:

```bash
docker compose exec -T db psql -U memoize -d memoize \
  -c "ALTER TABLE problem_memories ADD COLUMN IF NOT EXISTS ..."
```

Teammates on a fresh clone pick it up automatically; anyone with an existing
volume needs the same ALTER (or `docker compose down -v`, which destroys data).
Announce schema changes — they are the one thing that silently breaks another
developer's running setup.

## No vector index — on purpose

There is no `ivfflat`/`hnsw` index on `problems.embedding`. At 1,200 rows an
exact cosine scan is ~2ms, while an approximate index with the usual `lists=100`
measurably *hurts* recall. Add one only past ~10k rows.

## Embedding dimension

`problems.embedding` is `VECTOR(768)`, matching `gemini-embedding-001` at the
default output size. If you change `EMBEDDING_DIM` in `.env`, change the column
too — pgvector will reject mismatched inserts.


## Community contributions (`05_community.sql`)

Two things a user-contributed problem needs that the corpus dump did not.

**Three columns on `problems`.** `origin` (`corpus` | `community`), `confidence`
and `contribution_count`. Columns rather than a separate table, for the same
reason the company metadata is columns: a community problem is a problem, and
splitting it out would mean a join on every browse query and two shapes for one
concept.

**One table, `contributions`.** One row per person who described a problem, with
their raw transcript and follow-up answers. A counter alone would have been
enough to compute confidence, but not to show *why* a problem sits at 0.65 —
and being able to put the three separate recollections on screen is most of the
point.

```text
confidence = min(0.95, 0.35 + 0.15 × (contribution_count − 1))
```

Corpus rows are fixed at 1.0. Community rows never reach it: a remembered
statement does not become as trustworthy as one fetched from LeetCode, however
many people remember it the same way.

Slug collisions are resolved by suffixing (`-2`, `-3`), never by upserting. Two
people describing "that sliding window thing" are not necessarily describing the
same problem, and merging them on slug would quietly corrupt the very signal
confidence is measuring.

`idx_problems_topics` (GIN) was added alongside it — browsing by topic is a
first-class nav axis now, so it gets the same treatment `companies` has.

### Applying it to an existing volume

Docker only runs `database/init/*.sql` on an **empty** volume, so an existing
database needs it by hand:

```bash
docker exec -i memoize-db psql -U recollect -d recollect < database/init/05_community.sql
```

Every statement is `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`, so re-running it
is harmless.
