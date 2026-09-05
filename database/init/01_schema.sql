-- Recollect MVP schema.
-- Runs automatically on first `docker compose up` (empty volume only).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- Known coding problems + their embeddings (the RAG corpus).
CREATE TABLE IF NOT EXISTS problems (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    platform    TEXT,
    difficulty  TEXT,
    source_url  TEXT,
    embedding   VECTOR(768),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per user memory (the "Problem Genome" the AI extracted).
CREATE TABLE IF NOT EXISTS problem_memories (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id     UUID REFERENCES problems(id) ON DELETE SET NULL,
    concepts       TEXT[] NOT NULL DEFAULT '{}',
    operations     TEXT[] NOT NULL DEFAULT '{}',
    constraints    TEXT[] NOT NULL DEFAULT '{}',
    objective      TEXT,
    uncertainties  TEXT[] NOT NULL DEFAULT '{}',
    raw_transcript TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS test_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id      UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    input           TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS submissions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    code       TEXT NOT NULL,
    language   TEXT NOT NULL,
    status     TEXT,
    runtime    TEXT,
    memory     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_test_cases_problem  ON test_cases(problem_id);
CREATE INDEX IF NOT EXISTS idx_submissions_problem ON submissions(problem_id);

-- Cosine-distance ANN index. Fine to create on an empty table for a hackathon
-- corpus; rebuild after a large bulk load if recall looks off.
CREATE INDEX IF NOT EXISTS idx_problems_embedding
    ON problems USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
