-- Community contributions.
--
-- A problem can now enter the corpus two ways: it shipped with the LeetCode
-- dump (`origin = 'corpus'`), or a user described one we did not have
-- (`origin = 'community'`). The difference is how much we trust it, so trust is
-- a stored number rather than an implicit assumption.
--
-- `confidence` is the corpus-level twin of CLAUDE.md §19: a community problem
-- is an inference until other people independently describe the same thing.

ALTER TABLE problems
    ADD COLUMN IF NOT EXISTS origin             TEXT    NOT NULL DEFAULT 'corpus',
    ADD COLUMN IF NOT EXISTS confidence         REAL    NOT NULL DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS contribution_count INTEGER NOT NULL DEFAULT 0;

-- One row per person who described this problem. Kept rather than folded into
-- a counter because the confidence rule needs to be auditable on stage: we can
-- show the three separate recollections that took a problem from 0.35 to 0.65.
CREATE TABLE IF NOT EXISTS contributions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    -- 'created' seeded the problem; 'confirmed' independently matched it.
    kind       TEXT NOT NULL DEFAULT 'confirmed',
    transcript TEXT NOT NULL,
    -- The follow-up answers (company, difficulty, input/output shape, ...).
    details    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contributions_problem ON contributions(problem_id);

-- Browse-by-topic is a first-class nav axis now, so it gets the same GIN
-- treatment `companies` has.
CREATE INDEX IF NOT EXISTS idx_problems_topics ON problems USING gin (topics);
CREATE INDEX IF NOT EXISTS idx_problems_origin ON problems(origin);
