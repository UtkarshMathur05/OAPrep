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
  /**
   * How the solution reads stdin, in prose. Solutions here are whole programs
   * over stdin, not function bodies, so the statement alone never says which
   * line the target is on. Empty when nobody has pinned the format down —
   * render nothing rather than a guess.
   */
  io_format: string
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
  /**
   * False when this problem cannot be attempted here at all — a SQL question or
   * a class-design one. Carried on the reconstruction so the recall flow can
   * link out instead of offering an editor that can never return a verdict.
   */
  solvable?: boolean
  unsolvable_reason?: string | null
  source_url?: string | null
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
  /** 'corpus' shipped with the LeetCode dump; 'community' came from a user. */
  origin: 'corpus' | 'community'
  /** 1.0 for corpus rows. Community rows start at 0.35 and climb. */
  confidence: number
  contribution_count: number
}

/** GET /problems/{id} — accepts a UUID or a slug. */
export interface ProblemDetail extends ProblemSummary {
  description: string
  /**
   * 'functional' — write the function the statement describes, the way the
   * statement describes it. 'stdin' — write a whole program that reads stdin,
   * which is where class-design problems and anything the harness has no type
   * for still live.
   */
  exec_mode: 'functional' | 'stdin'
  /** {name, params, return} when functional. The editor does not read it. */
  signature: Record<string, unknown> | null
  /** Our language id -> starter code. Per problem, because the signature is. */
  code_snippets: Record<string, string>
  /**
   * Languages this problem can actually run in. Shorter than the full list for
   * a functional problem — offering one that fails the moment you press Run is
   * worse than not offering it.
   */
  runnable_languages: string[]
  /**
   * How the solution reads stdin, in prose. Solutions here are whole programs
   * over stdin, not function bodies, so the statement alone never says which
   * line the target is on. Empty when nobody has pinned the format down —
   * render nothing rather than a guess.
   */
  io_format: string
  has_embedding: boolean
  test_case_count: number
  /**
   * False when the problem cannot be attempted here at all — a SQL question, or
   * a class-design one where the judge calls a sequence of methods. Neither is a
   * program that reads stdin, so we send people upstream rather than open an
   * editor that can never return a verdict.
   */
  solvable: boolean
  /** Why, in one sentence, when `solvable` is false. */
  unsolvable_reason: string | null
}

// ------------------------------------------------------------------ accounts

/** What the browser is allowed to know about an account. Never a password. */
export interface PublicUser {
  id: string
  email: string
  email_verified: boolean
  display_name: string
  avatar_url: string | null
  /** False for an account that only ever signs in with GitHub or Google. */
  has_password: boolean
  providers: string[]
}

/** What signing in pulled across from the anonymous browser session. */
export interface Claimed {
  submissions: number
  contributions: number
  problems: number
}

export interface AuthResponse {
  user: PublicUser
  claimed: Claimed
}

export interface MeResponse {
  /** Null when signed out, which is a normal 200 rather than a 401. */
  user: PublicUser | null
  /** Problems a signed-out visitor may still run. Null once signed in. */
  guest_runs_left: number | null
}

export interface ProblemListResponse {
  total: number
  limit: number
  offset: number
  problems: ProblemSummary[]
}

export type ProblemSort =
  | 'popularity' | 'title' | 'difficulty' | 'companies' | 'acceptance' | 'newest'

export interface ProblemListParams {
  limit?: number
  offset?: number
  difficulty?: string
  company?: string
  /** LeetCode tag, verbatim casing: 'Dynamic Programming'. */
  topic?: string
  origin?: 'corpus' | 'community'
  search?: string
  sort?: ProblemSort
}

// GET /problems/facets
export interface Facet {
  name: string
  count: number
}
export interface FacetsResponse {
  companies: Facet[]
  topics: Facet[]
  difficulties: Facet[]
  totals: { problems: number; community: number; companies: number; topics: number }
}

// POST /contribute/match
export interface ContributeMatchRequest {
  transcript: string
  top_k?: number
}
export interface ContributeMatchResponse {
  memory_id: string | null
  memory: Genome
  candidates: Candidate[]
  /** The top candidate is close enough that creating a row would duplicate it. */
  likely_duplicate: boolean
}

// POST /contribute
export interface ContributeDetails {
  title?: string
  difficulty?: string
  topics?: string[]
  companies?: string[]
  input_format?: string
  output_format?: string
  example?: string
  constraints?: string
}
export interface ContributeRequest {
  transcript: string
  details?: ContributeDetails
  /** Set to corroborate an existing problem instead of creating a new one. */
  confirm_problem_id?: string
}
export interface ContributeResponse {
  problem_id: string
  slug: string
  title: string
  action: 'created' | 'confirmed'
  confidence: number
  contribution_count: number
  test_case_count: number
  message: string
}

// GET /languages
export interface Language {
  id: string
  label: string
  /** Monaco's own language id, for syntax highlighting. */
  monaco: string
  /** A whole program that reads stdin and prints an answer. */
  starter: string
}

// GET /progress
export interface SessionProgress {
  solved: string[]
  attempted: string[]
  runs: number
  solved_count: number
}

// GET /progress/{id}
export interface ProblemProgress {
  runs: number
  submissions: number
  solved: boolean
  best_passed: number
  total: number
}

// POST /verify
export interface VerifyRequest {
  problem_id: string
  code: string
  language: string
  /**
   * 'run' is a trial; 'submit' is the claim that the solution is finished.
   * Only an accepted submit marks the problem complete.
   */
  kind?: 'run' | 'submit'
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

  submission_id?: string | null
  kind: 'run' | 'submit'
  all_passed: boolean

  /** This caller's standing on this problem, after the call. */
  solved: boolean
  runs: number
  submissions: number

  /**
   * The signed-out visitor has used up their free problems. Not an error: the
   * code never ran and there is nothing wrong with it, so the editor shows a
   * sign-in prompt rather than a failure.
   */
  requires_sign_in: boolean
}
