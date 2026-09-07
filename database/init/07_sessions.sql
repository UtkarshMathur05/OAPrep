-- Sessions, submissions and completion.
--
-- `session_id` is the seam auth slots into. Today it is an anonymous UUID the
-- browser generates and stores; when accounts land it becomes (or joins to) a
-- user id, and `app/identity.py` is the only file that has to change. Adding
-- the column now means existing rows are attributable later instead of being
-- an undifferentiated pile.

ALTER TABLE submissions
    -- 'run' is a trial; 'submit' is the user claiming the solution is done.
    -- LeetCode's distinction, and worth keeping: only submits mark completion,
    -- but runs are what you count to show effort.
    ADD COLUMN IF NOT EXISTS kind       TEXT    NOT NULL DEFAULT 'run',
    ADD COLUMN IF NOT EXISTS passed     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total      INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS session_id UUID;

ALTER TABLE contributions
    ADD COLUMN IF NOT EXISTS session_id UUID;

-- Every progress query is "what has this session done to this problem".
CREATE INDEX IF NOT EXISTS idx_submissions_session
    ON submissions(session_id, problem_id);

-- One corroboration per session per problem.
--
-- Confidence rises with the number of *independent* accounts, so without this
-- one person clicking "that's it" five times takes a problem from 0.35 to 0.95
-- on their own. Partial, because anonymous rows (session_id IS NULL) predate
-- this and must not collide with each other.
CREATE UNIQUE INDEX IF NOT EXISTS uq_contribution_per_session
    ON contributions(problem_id, session_id)
    WHERE session_id IS NOT NULL;
