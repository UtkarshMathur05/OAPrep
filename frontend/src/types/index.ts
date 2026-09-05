// Shared API types. These mirror backend/app/schemas/*.py — keep them in sync.

export interface Genome {
  concepts: string[]
  operations: string[]
  objective: string | null
  constraints: string[]
  data_structures: string[]
  algorithm_hints: string[]
  uncertainties: string[]
}

// POST /memory
export interface MemoryRequest {
  transcript: string
}
export interface MemoryResponse {
  memory_id: string | null
  memory: Genome
}

// POST /search
export interface SearchRequest {
  memory: Genome
  memory_id?: string
  top_k?: number
  /** Lowercase company slugs. Filters the corpus before the vector search. */
  companies?: string[]
}
export interface Candidate {
  id: string
  title: string
  confidence: number
  platform?: string | null
  difficulty?: string | null
  reason?: string | null
  topics: string[]
  /** Truncated for display — use company_count for the real total. */
  companies: string[]
  company_count: number
}
export interface SearchResponse {
  candidates: Candidate[]
}

// POST /reconstruct
export interface ReconstructRequest {
  memory_id: string
  candidate_id: string
}
export interface Example {
  input: string
  output: string
  explanation?: string | null
}
/**
 * How a part of the reconstructed problem came to be known.
 * CLAUDE.md §19 — an inference must never be rendered as a remembered fact.
 * Render `inferred` visually distinct: the same treatment uncertainties get on
 * the memory card.
 */
export type Provenance = 'remembered' | 'retrieved' | 'inferred'

export interface Problem {
  id?: string | null
  title: string
  description: string
  constraints: string[]
  examples: Example[]
  confidence: number
  /**
   * Field name -> provenance. Expected keys: 'title', 'description',
   * 'constraints', 'examples'. A missing key means the pipeline made no
   * claim — render it unlabelled rather than assuming. Partial<> because of
   * that: reading an absent key must type as undefined, which is how
   * ProblemDisplay already handles it.
   */
  provenance: Partial<Record<string, Provenance>>
  /** Reader-facing caveats, e.g. "You recalled obstacles; this problem has none." */
  notes: string[]
  /** Seeds the Monaco buffer on the Practice screen. Python only. */
  starter_code?: string | null
}
export interface ReconstructResponse {
  problem: Problem
}

// GET /problems
export interface ProblemSummary {
  id: string
  slug: string
  title: string
  difficulty?: string | null
  platform?: string | null
  source_url?: string | null
  topics: string[]
  /** Truncated for display — use company_count for the real total. */
  companies: string[]
  company_count: number
  popularity: number
  acceptance?: number | null
  recency?: string | null
}

/** GET /problems/{id} — accepts a UUID or a slug. */
export interface ProblemDetail extends ProblemSummary {
  description: string
  has_embedding: boolean
  test_case_count: number
}

export interface ProblemListResponse {
  total: number
  limit: number
  offset: number
  problems: ProblemSummary[]
}

export interface ProblemListParams {
  limit?: number
  offset?: number
  difficulty?: string
  company?: string
  search?: string
}

// POST /verify
export interface VerifyRequest {
  problem_id: string
  code: string
  language: string
}
export interface TestResult {
  index: number
  passed: boolean
  input?: string | null
  expected_output?: string | null
  actual_output?: string | null
}
export interface VerifyResponse {
  status: string
  passed: number
  total: number
  runtime?: string | null
  memory?: string | null
  results: TestResult[]
}
