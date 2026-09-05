-- Five hand-written problems so /search returns something on a bare clone.
-- Superseded by the real corpus: see ai/corpus/README.md. Once you have run the
-- corpus pipeline, these rows are harmless duplicates of the same slugs and the
-- loader's ON CONFLICT (slug) will fold them together.

INSERT INTO problems (slug, title, description, platform, difficulty, source_url)
VALUES
  ('minimum-path-sum', 'Minimum Path Sum',
   'Given a m x n grid filled with non-negative numbers, find a path from top left to bottom right which minimizes the sum of all numbers along its path. You can only move either down or right at any point in time.',
   'leetcode', 'medium', 'https://leetcode.com/problems/minimum-path-sum/'),
  ('unique-paths', 'Unique Paths',
   'A robot is located at the top-left corner of a m x n grid. The robot can only move either down or right. How many possible unique paths are there to reach the bottom-right corner?',
   'leetcode', 'medium', 'https://leetcode.com/problems/unique-paths/'),
  ('coin-change', 'Coin Change',
   'Given an integer array coins and an integer amount, return the fewest number of coins needed to make up that amount. If it cannot be made up by any combination, return -1.',
   'leetcode', 'medium', 'https://leetcode.com/problems/coin-change/'),
  ('number-of-islands', 'Number of Islands',
   'Given an m x n 2D binary grid which represents a map of ''1''s (land) and ''0''s (water), return the number of islands.',
   'leetcode', 'medium', 'https://leetcode.com/problems/number-of-islands/'),
  ('longest-increasing-subsequence', 'Longest Increasing Subsequence',
   'Given an integer array nums, return the length of the longest strictly increasing subsequence.',
   'leetcode', 'medium', 'https://leetcode.com/problems/longest-increasing-subsequence/')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO test_cases (problem_id, input, expected_output)
SELECT id, '3 3
1 3 1
1 5 1
4 2 1', '7' FROM problems WHERE title = 'Minimum Path Sum'
ON CONFLICT DO NOTHING;

INSERT INTO test_cases (problem_id, input, expected_output)
SELECT id, '3 7', '28' FROM problems WHERE title = 'Unique Paths'
ON CONFLICT DO NOTHING;
