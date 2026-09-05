// Mock payloads so the frontend runs with no backend.
// Used by services/api.ts when VITE_USE_MOCK=true.

import type {
  Genome, MemoryResponse, SearchResponse, ReconstructResponse, VerifyResponse,
  ProblemDetail, ProblemListResponse,
} from '../types'

export const mockGenome: Genome = {
  concepts: ['grid', 'dynamic programming'],
  operations: ['move right', 'move down'],
  objective: 'minimize cost',
  constraints: [],
  data_structures: ['2d array'],
  algorithm_hints: ['memoization'],
  uncertainties: ['maybe there were obstacles'],
}

export const mockMemoryResponse: MemoryResponse = {
  memory_id: 'mock-memory-1',
  memory: mockGenome,
}

export const mockSearchResponse: SearchResponse = {
  candidates: [
    { id: '1', title: 'Minimum Path Sum', confidence: 0.91, difficulty: 'medium', reason: 'Grid with down/right moves, minimizing a sum.' },
    { id: '2', title: 'Unique Paths', confidence: 0.72, difficulty: 'medium', reason: 'Same movement rules, but counts paths instead of minimizing.' },
    { id: '3', title: 'Dungeon Game', confidence: 0.48, difficulty: 'hard', reason: 'Grid DP, but the objective is survival not cost.' },
  ],
}

export const mockReconstructResponse: ReconstructResponse = {
  problem: {
    id: '1',
    title: 'Minimum Path Sum',
    description:
      'Given an m x n grid filled with non-negative numbers, find a path from the ' +
      'top-left to the bottom-right which minimizes the sum of all numbers along ' +
      'the path. You may only move either down or right at any point in time.',
    constraints: ['1 <= m, n <= 200', '0 <= grid[i][j] <= 200'],
    examples: [
      { input: '[[1,3,1],[1,5,1],[4,2,1]]', output: '7', explanation: 'The path 1 → 3 → 1 → 1 → 1 has the minimum sum.' },
    ],
    confidence: 0.91,
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

export const mockStarterCode = `class Solution:
    def minPathSum(self, grid: list[list[int]]) -> int:
        pass
`
