-- Accounts.
--
-- §20b said `app/identity.py` was the seam auth would slot into, and it was —
-- but not by having it return a user id in place of a session id. One column
-- holding two id spaces cannot be foreign-keyed, cannot tell "anonymous" from
-- "user X", and turns claiming into a destructive rewrite. So `user_id` sits
-- *beside* `session_id` everywhere: anonymous rows keep their session, signed-in
-- rows carry both, and claiming is an UPDATE that fills in the blank.
--
-- Two tables, not four. Providers are columns because there are exactly two of
-- them, the same reasoning §8 used for corpus metadata; and password-reset
-- tokens are signed and stateless rather than stored (see `password_changed_at`).

CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email          TEXT NOT NULL,
    -- Only ever true when a provider asserted it, or the user followed a link
    -- we sent. It gates OAuth account-linking, so it is a security control
    -- rather than a display detail.
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    -- NULL for an account that only ever signs in with GitHub or Google. Such a
    -- user has no password to guess, which is the point.
    password_hash  TEXT,
    -- Bumped on every password change and baked into reset tokens, so using one
    -- invalidates every token issued before it. That is what makes a signed,
    -- stateless token single-use without a table to keep it in.
    password_changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    display_name   TEXT,
    avatar_url     TEXT,
    github_id      TEXT,
    google_id      TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Case-insensitive: nobody thinks Ada@x.com and ada@x.com are two accounts, and
-- letting them be two is how you get a confusing duplicate nobody can sign into.
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email  ON users (lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_github ON users (github_id) WHERE github_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_google ON users (google_id) WHERE google_id IS NOT NULL;

-- Server-side sessions, so signing out actually ends the session.
--
-- A self-contained JWT would need no table, and could not be revoked: a stolen
-- one stays valid until it expires, and "sign out everywhere" becomes a lie.
-- A row per session is one indexed lookup per request and buys real logout.
CREATE TABLE IF NOT EXISTS auth_sessions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- SHA-256 of the cookie value. The token itself is never stored, so reading
    -- this table does not hand anybody a live session.
    token_hash TEXT NOT NULL UNIQUE,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);

-- --------------------------------------------------------------- attribution

ALTER TABLE submissions
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE contributions
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;

-- Who submitted a community problem. This did not exist in any form: only
-- `contributions` recorded a session, so "questions I added" was unanswerable
-- regardless of whether accounts existed.
ALTER TABLE problems
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_submissions_user   ON submissions(user_id, problem_id);
CREATE INDEX IF NOT EXISTS idx_contributions_user ON contributions(user_id);
CREATE INDEX IF NOT EXISTS idx_problems_created_by ON problems(created_by)
    WHERE created_by IS NOT NULL;

-- One corroboration per *account* per problem.
--
-- `uq_contribution_per_session` stopped one browser voting repeatedly, but a
-- session id is free to mint, so it never made the confidence formula honest —
-- §20b says as much. This is the index that does. The per-session one stays for
-- signed-out traffic.
CREATE UNIQUE INDEX IF NOT EXISTS uq_contribution_per_user
    ON contributions(problem_id, user_id)
    WHERE user_id IS NOT NULL;
