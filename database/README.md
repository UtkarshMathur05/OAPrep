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
| `init/02_seed.sql` | A handful of sample problems + test cases |

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

## Embedding dimension

`problems.embedding` is `VECTOR(768)`, matching `gemini-embedding-001` at the
default output size. If you change `EMBEDDING_DIM` in `.env`, change the column
too — pgvector will reject mismatched inserts.
