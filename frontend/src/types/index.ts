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
/** Where a piece of the reconstructed problem came from. Render `inferred`
 *  visually distinct - same treatment as uncertainties on the memory card. */
export type Provenance = 'remembered' | 'retrieved' | 'inferred'

export interface Problem {
  id?: string | null
  title: string
  description: string
  constraints: string[]
  examples: Example[]
  confidence: number
  /** Keyed by field name: title / description / constraints / examples. */
  provenance: Record<string, Provenance>
  /** Reader-facing caveats, e.g. "You recalled obstacles; this problem has none." */
  notes: string[]
  /** Seeds the Monaco buffer on the Practice screen. */
  starter_code?: string | null
}
export interface ReconstructResponse {
  problem: Problem
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
