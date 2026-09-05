// Mock payloads so the frontend runs with no backend.
// Used by services/api.ts when VITE_USE_MOCK=true.
//
// These mirror what the real pipeline actually returns for the golden demo
// memory ("a grid problem, right or down, minimum cost, maybe obstacles"), so
// building against them builds against the truth.

import type {
  Genome, MemoryResponse, SearchResponse, ReconstructResponse, VerifyResponse,
  ProblemDetail, ProblemListResponse,
} from '../types'

export const mockGenome: Genome = {
  concepts: ['grid'],
  operations: ['move right', 'move down'],
  objective: 'find minimum cost',
  constraints: [],
  data_structures: ['2d array'],
  algorithm_hints: [],
  // Render these visually distinct from the certain fields - this is the screen
  // that shows Recollect handles doubt.
  uncertainties: ['whether there were obstacles'],
}

export const mockMemoryResponse: MemoryResponse = {
  memory_id: 'mock-memory-1',
  memory: mockGenome,
}

export const mockSearchResponse: SearchResponse = {
  candidates: [
    {
      id: '1', title: 'Minimum Path Sum', confidence: 0.98, difficulty: 'medium',
      reason: 'Matches all details: a 2D grid, moving only down or right, and minimizing the path sum.',
      topics: ['Array', 'Dynamic Programming', 'Matrix'],
      companies: ['google', 'amazon', 'microsoft', 'apple', 'bloomberg', 'adobe'],
      company_count: 17,
    },
    {
      id: '2', title: 'Dungeon Game', confidence: 0.80, difficulty: 'hard',
      reason: 'A 2D grid moving down and right to minimize cost, but the objective is survival.',
      topics: ['Array', 'Dynamic Programming', 'Matrix'],
      companies: ['amazon', 'microsoft', 'google'],
      company_count: 8,
    },
    {
      id: '3', title: 'Unique Paths', confidence: 0.55, difficulty: 'medium',
      reason: 'Same movement rules, but counts paths instead of minimizing a cost.',
      topics: ['Math', 'Dynamic Programming', 'Combinatorics'],
      companies: ['google', 'amazon', 'bloomberg'],
      company_count: 20,
    },
  ],
}

export const mockReconstructResponse: ReconstructResponse = {
  problem: {
    id: '1',
    title: 'Minimum Path Sum',
    description:
      'Given an m x n grid filled with non-negative numbers, find a path from the ' +
      'top-left corner to the bottom-right corner which minimizes the sum of all ' +
      'numbers along its path.\n\nYou can only move either down or right at any ' +
      'point in time.\n\nInput Format:\nThe first line contains two space-separated ' +
      'integers m and n, the number of rows and columns.\nThe next m lines each ' +
      'contain n space-separated integers, the grid values.\n\nOutput Format:\n' +
      'Print a single integer, the minimum path sum.',
    constraints: ['1 <= m, n <= 200', '0 <= grid[i][j] <= 200'],
    // stdin/stdout, not function-call shorthand: Judge0 runs a script (CLAUDE.md §9).
    examples: [
      { input: '3 3\n1 3 1\n1 5 1\n4 2 1', output: '7', explanation: 'The path 1 -> 3 -> 1 -> 1 -> 1 minimizes the sum.' },
      { input: '2 3\n1 2 3\n4 5 6', output: '12', explanation: 'The path 1 -> 2 -> 3 -> 6.' },
    ],
    confidence: 0.95,
    // Mark `inferred` sections visually distinct: never present something the
    // model filled in as something the user recalled.
    provenance: {
      title: 'retrieved',
      description: 'inferred',
      constraints: 'retrieved',
      examples: 'inferred',
    },
    notes: [
      'You were uncertain about whether there were obstacles; Minimum Path Sum does not feature obstacles. If you remember obstacles, you might be thinking of Unique Paths II.',
    ],
    starter_code: mockStarterCodeFor(),
  },
}

export const mockVerifyResponse: VerifyResponse = {
  status: 'Accepted',
  passed: 12,
  total: 12,
  runtime: '0.21s',
  memory: '18MB',
  results: [],
}

// Reads stdin and prints stdout, matching how Judge0 executes submissions.
function mockStarterCodeFor(): string {
  return [
    'import sys',
    '',
    'def main():',
    '    data = sys.stdin.read().split()',
    '    m, n = int(data[0]), int(data[1])',
    '    grid = []',
    '    idx = 2',
    '    for _ in range(m):',
    '        grid.append([int(x) for x in data[idx:idx + n]])',
    '        idx += n',
    '',
    '    # your solution here',
    '    print(0)',
    '',
    'if __name__ == "__main__":',
    '    main()',
  ].join('\n')
}

export const mockStarterCode = mockStarterCodeFor()

export const mockProblemList: ProblemListResponse = {
  total: 3,
  limit: 20,
  offset: 0,
  problems: [
    {
      id: '1fa55ea2-04b0-477d-ac38-8605a476e032',
      slug: 'minimum-path-sum',
      title: 'Minimum Path Sum',
      difficulty: 'medium',
      platform: 'leetcode',
      source_url: 'https://leetcode.com/problems/minimum-path-sum/',
      topics: ['Array', 'Dynamic Programming', 'Matrix'],
      companies: ['amazon', 'google', 'microsoft'],
      company_count: 41,
      popularity: 812.5,
      acceptance: 64.1,
      recency: '3mo',
    },
    {
      id: 'c494f9b7-249c-4b42-ae40-3934842375cf',
      slug: 'two-sum',
      title: 'Two Sum',
      difficulty: 'easy',
      platform: 'leetcode',
      source_url: 'https://leetcode.com/problems/two-sum/',
      topics: ['Array', 'Hash Table'],
      companies: ['accenture', 'adobe', 'amazon', 'apple', 'google'],
      company_count: 126,
      popularity: 9775.0,
      acceptance: 57.8,
      recency: '30d',
    },
    {
      id: 'e9871b85-761a-45da-b95a-b076b7572cb9',
      slug: 'unique-paths',
      title: 'Unique Paths',
      difficulty: 'medium',
      platform: 'leetcode',
      source_url: 'https://leetcode.com/problems/unique-paths/',
      topics: ['Math', 'Dynamic Programming', 'Combinatorics'],
      companies: ['amazon', 'bloomberg', 'google'],
      company_count: 28,
      popularity: 431.0,
      acceptance: 65.2,
      recency: '6mo',
    },
  ],
}

export const mockProblemDetail: ProblemDetail = {
  ...mockProblemList.problems[0],
  description:
    'Given a m x n grid filled with non-negative numbers, find a path from top ' +
    'left to bottom right which minimizes the sum of all numbers along its path. ' +
    'You can only move either down or right at any point in time.',
  has_embedding: true,
  test_case_count: 5,
}
