-- The stdin/stdout contract, written down.
--
-- Every solution here is a whole program that reads stdin and prints an answer
-- (CLAUDE.md §9). That makes the input format part of the problem: a statement
-- fetched from a function-signature platform says "given an array nums and an
-- integer target" and never says which line the target is on. Without this
-- column the user has to guess the shape from the examples, and the generator
-- has nothing to keep successive reconstructions agreeing with each other.
--
-- Nullable: most corpus rows have no tests yet, and inventing a format for a
-- problem nobody has run is exactly the confident fabrication §16 forbids.
ALTER TABLE problems
    ADD COLUMN IF NOT EXISTS io_format TEXT;

COMMENT ON COLUMN problems.io_format IS
    'Human-readable stdin spec. Authoritative once set: test cases that do not '
    'parse under it must not be stored.';
