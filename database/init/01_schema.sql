-- Memoize MVP schema.
-- Runs automatically on first `docker compose up` (empty volume only).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- Known coding problems + their embeddings (the RAG corpus).
CREATE TABLE IF NOT EXISTS problems (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT UNIQUE NOT NULL,
    leetcode_id INTEGER,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    platform    TEXT DEFAULT 'leetcode',
    difficulty  TEXT,
    source_url  TEXT,
    -- LeetCode topicTags: strong retrieval signal, maps onto the genome's
    -- `concepts` and `data_structures` fields.
    topics      TEXT[] NOT NULL DEFAULT '{}',
    -- Company metadata from data/leetcode-companywise-interview-questions.
    -- Lets the user narrow recall with "it was a Google question", and gives
    -- reranking a popularity prior.
    companies     TEXT[] NOT NULL DEFAULT '{}',
    company_count INTEGER NOT NULL DEFAULT 0,
    popularity    REAL    NOT NULL DEFAULT 0,   -- summed Frequency % across companies
    acceptance    REAL,                          -- LeetCode acceptance rate, %
    recency       TEXT,                          -- 30d | 3mo | 6mo | older
    description_source TEXT,                     -- leetcode | gemini
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
    -- The Genome carries these too; without columns they were silently dropped
    -- on save, and /reconstruct reloads the memory to prompt Gemini.
    data_structures TEXT[] NOT NULL DEFAULT '{}',
    algorithm_hints TEXT[] NOT NULL DEFAULT '{}',
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

-- Company filter: `WHERE companies @> ARRAY['google']`.
CREATE INDEX IF NOT EXISTS idx_problems_companies ON problems USING gin (companies);

CREATE INDEX IF NOT EXISTS idx_test_cases_problem  ON test_cases(problem_id);
CREATE INDEX IF NOT EXISTS idx_submissions_problem ON submissions(problem_id);

-- No ANN index on purpose. At hackathon corpus size (500-5000 problems) an exact
-- cosine scan is ~2ms, while ivfflat with the usual lists=100 measurably hurts
-- recall. Add one only if the corpus grows past ~10k rows.
