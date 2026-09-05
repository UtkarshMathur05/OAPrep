// Mock payloads so the frontend runs with no backend.
// Used by services/api.ts when VITE_USE_MOCK=true.

import type {
  Genome, MemoryResponse, SearchResponse, ReconstructResponse, VerifyResponse,
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

export const mockStarterCode = `class Solution:
    def minPathSum(self, grid: list[list[int]]) -> int:
        pass
`
