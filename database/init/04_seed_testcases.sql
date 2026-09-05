-- Test cases for a few well-known problems, so POST /verify can be demoed
-- before ai/verification/test_generator.py exists.
--
-- Runs AFTER 03_corpus.sql (docker runs init scripts in filename order) because
-- it references corpus problems by slug. It no longer inserts problems of its
-- own: it used to, and those rows shadowed the real corpus entries via
-- ON CONFLICT (slug) DO NOTHING, leaving five popular problems with no
-- embedding and therefore invisible to semantic search.
--
-- Format matches Judge0: `input` goes to stdin verbatim, stdout is compared to
-- `expected_output` after trailing whitespace is stripped.

INSERT INTO test_cases (problem_id, input, expected_output)
SELECT id, E'3 3\n1 3 1\n1 5 1\n4 2 1', '7'
FROM problems WHERE slug = 'minimum-path-sum'
  AND NOT EXISTS (SELECT 1 FROM test_cases t WHERE t.problem_id = problems.id);

INSERT INTO test_cases (problem_id, input, expected_output)
SELECT id, E'2 2\n1 2\n1 1', '3'
FROM problems WHERE slug = 'minimum-path-sum'
  AND (SELECT count(*) FROM test_cases t WHERE t.problem_id = problems.id) < 2;

INSERT INTO test_cases (problem_id, input, expected_output)
SELECT id, '3 7', '28'
FROM problems WHERE slug = 'unique-paths'
  AND NOT EXISTS (SELECT 1 FROM test_cases t WHERE t.problem_id = problems.id);
