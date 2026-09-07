-- Functional execution: solve a problem by writing the function, not a parser.
--
-- Judge0 only speaks stdin/stdout, and that stays true — but it becomes
-- transport rather than the interface. A per-language harness deserialises the
-- arguments, calls the solution, and serialises what it returns, so the person
-- solving writes `def minPathSum(self, grid)` and never sees stdin.
--
-- Why this reverses CLAUDE.md §9: stdin/stdout made eleven languages nearly
-- free, which was the right trade in 36 hours. It is the wrong trade for a
-- problem bank, because the statements are written for a function signature and
-- describe arguments as array literals. Every problem was therefore telling the
-- reader one thing and the runner another.
--
-- The alternative was generating a stdin-parsing preamble per problem per
-- language. That costs problems x languages (~37,000 artifacts, each a fresh
-- chance to be subtly wrong) against languages alone (11, hand-written once).

ALTER TABLE problems
    -- 'stdin' is the old contract and stays the default: nothing that works
    -- today changes mode without being migrated deliberately.
    ADD COLUMN IF NOT EXISTS exec_mode     TEXT NOT NULL DEFAULT 'stdin',
    -- {"name": "minPathSum",
    --  "params": [{"name": "grid", "type": "integer[][]"}],
    --  "return": {"type": "integer"}}
    ADD COLUMN IF NOT EXISTS signature     JSONB,
    -- langSlug -> starter code. Per problem, because the signature is.
    ADD COLUMN IF NOT EXISTS code_snippets JSONB,
    -- How a returned answer is compared. 'exact' is the default; problems that
    -- accept any order or any valid answer need to say so, or a correct
    -- solution gets told it is wrong.
    ADD COLUMN IF NOT EXISTS judge_mode    TEXT NOT NULL DEFAULT 'exact';

DO $$
BEGIN
    ALTER TABLE problems ADD CONSTRAINT problems_exec_mode_chk
        CHECK (exec_mode IN ('stdin', 'functional'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE problems ADD CONSTRAINT problems_judge_mode_chk
        CHECK (judge_mode IN ('exact', 'unordered', 'set'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- A functional problem without a signature cannot be run at all: the harness
-- has nothing to generate. Refuse the row rather than discover it at submit.
DO $$
BEGIN
    ALTER TABLE problems ADD CONSTRAINT problems_functional_needs_signature
        CHECK (exec_mode <> 'functional' OR signature IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON COLUMN problems.exec_mode IS
    'functional: test_cases.input holds one JSON argument per line and '
    'expected_output holds the JSON return value. stdin: both are literal text.';
