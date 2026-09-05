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
docker compose exec -T db psql -U recollect -d recollect < database/init/01_schema.sql
```

## Connecting

```bash
docker compose exec db psql -U recollect -d recollect
```

`DATABASE_URL=postgresql://recollect:recollect@localhost:5432/recollect`

## Schema changes after first boot

`init/*.sql` runs **only on an empty volume**, so editing it does nothing to a
database that already exists. Apply the change by hand as well:

```bash
docker compose exec -T db psql -U recollect -d recollect \
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
