// The only place the frontend talks to the backend.
// With VITE_USE_MOCK=true every call resolves from data/mockData.ts instead,
// so the UI can be built before the backend exists.

import axios from 'axios'
import { getSessionId } from '../lib/session'
import type {
  ProblemDetail, ProblemListParams, ProblemListResponse,
  MemoryRequest, MemoryResponse,
  SearchRequest, SearchResponse,
  ReconstructRequest, ReconstructResponse,
  VerifyRequest, VerifyResponse,
  Language, ProblemProgress, SessionProgress,
  FacetsResponse,
  ContributeMatchRequest, ContributeMatchResponse,
  ContributeRequest, ContributeResponse,
  AuthResponse, MeResponse, PublicUser,
} from '../types'
import {
  mockMemoryResponse, mockSearchResponse, mockReconstructResponse, mockVerifyResponse,
  mockProblemList, mockProblemDetail, mockFacets,
} from '../data/mockData'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

/**
 * Where the API is.
 *
 * Always ends in `/api`. Served from one origin, `/problems` is both a page and
 * an endpoint, so the API takes the prefix and the pages keep the clean URLs —
 * and the prefix is on in development too, so the deployed layout is the one
 * being exercised.
 *
 * Deployed this is the relative `/api`; locally it is the backend across the
 * port at `http://localhost:8000/api`. Trailing slashes are stripped so that
 * `${API_BASE}/auth/...` can never become the protocol-relative `//auth/...`,
 * which a browser reads as a hostname rather than a path.
 */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api')
  .replace(/\/+$/, '')

export const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  // The session cookie is httpOnly, so JavaScript never sees it — but axios
  // still has to be told to send it. Without this every request arrives signed
  // out and the symptom is "signing in appears to work, then does not".
  withCredentials: true,
})

// Every request carries the anonymous browser id, so no call site has to
// remember to. It stays after accounts land: it is what an unclaimed
// contribution or run is attributed to, and what sign-in claims.
client.interceptors.request.use((config) => {
  config.headers.set('X-Session-Id', getSessionId())
  return config
})

const mock = <T>(data: T, ms = 400): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(data), ms))

export async function extractMemory(body: MemoryRequest): Promise<MemoryResponse> {
  if (USE_MOCK) return mock(mockMemoryResponse)
  const { data } = await client.post<MemoryResponse>('/memory', body)
  return data
}

export async function searchCandidates(body: SearchRequest): Promise<SearchResponse> {
  if (USE_MOCK) return mock(mockSearchResponse)
  const { data } = await client.post<SearchResponse>('/search', body)
  return data
}

export async function reconstructProblem(body: ReconstructRequest): Promise<ReconstructResponse> {
  if (USE_MOCK) return mock(mockReconstructResponse)
  const { data } = await client.post<ReconstructResponse>('/reconstruct', body)
  return data
}

export async function listProblems(params: ProblemListParams = {}): Promise<ProblemListResponse> {
  if (USE_MOCK) return mock(mockProblemList)
  const { data } = await client.get<ProblemListResponse>('/problems', { params })
  return data
}

/** Accepts a UUID or a slug, e.g. getProblem('two-sum'). */
export async function getProblem(idOrSlug: string): Promise<ProblemDetail> {
  if (USE_MOCK) return mock(mockProblemDetail)
  const { data } = await client.get<ProblemDetail>(`/problems/${idOrSlug}`)
  return data
}

export async function verifySolution(body: VerifyRequest): Promise<VerifyResponse> {
  if (USE_MOCK) return mock(mockVerifyResponse, 900)
  const { data } = await client.post<VerifyResponse>('/verify', body)
  return data
}

export async function getFacets(): Promise<FacetsResponse> {
  if (USE_MOCK) return mock(mockFacets)
  const { data } = await client.get<FacetsResponse>('/problems/facets')
  return data
}

/** Step 1 of contributing: do we already have what they are describing? */
export async function matchContribution(
  body: ContributeMatchRequest,
): Promise<ContributeMatchResponse> {
  const { data } = await client.post<ContributeMatchResponse>('/contribute/match', body)
  return data
}

/** Step 2: create a community problem, or corroborate an existing one. */
export async function submitContribution(
  body: ContributeRequest,
): Promise<ContributeResponse> {
  const { data } = await client.post<ContributeResponse>('/contribute', body)
  return data
}

export async function getLanguages(): Promise<Language[]> {
  const { data } = await client.get<Language[]>('/languages')
  return data
}

/** Solved and attempted slugs for this session, for marking a listing. */
export async function getProgress(): Promise<SessionProgress> {
  const { data } = await client.get<SessionProgress>('/progress')
  return data
}

/** This session's standing on one problem. Accepts a UUID or a slug. */
export async function getProblemProgress(idOrSlug: string): Promise<ProblemProgress> {
  const { data } = await client.get<ProblemProgress>(`/progress/${idOrSlug}`)
  return data
}


// ------------------------------------------------------------------- accounts
//
// Not mocked. VITE_USE_MOCK exists so the UI can be built without a backend,
// and a fake sign-in that never sets a cookie would report success and then
// behave as signed out everywhere else — a worse failure than having no
// account at all. With mocks on, these simply fail and the UI stays signed out.

export async function getMe(): Promise<MeResponse> {
  const { data } = await client.get<MeResponse>('/auth/me')
  return data
}

export async function signUp(body: {
  email: string; password: string; display_name?: string
}): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>('/auth/signup', body)
  return data
}

export async function signIn(body: { email: string; password: string }): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>('/auth/signin', body)
  return data
}

export async function signOut(): Promise<void> {
  await client.post('/auth/signout')
}

export async function forgotPassword(email: string): Promise<void> {
  await client.post('/auth/forgot-password', { email })
}

export async function resetPassword(token: string, password: string): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>('/auth/reset-password', { token, password })
  return data
}

export async function verifyEmail(token: string): Promise<PublicUser> {
  const { data } = await client.post<PublicUser>('/auth/verify-email', { token })
  return data
}

export async function resendVerification(): Promise<void> {
  await client.post('/auth/resend-verification')
}

/**
 * Where to send the browser to start an OAuth sign-in.
 *
 * A full-page navigation, not a fetch: the provider redirects the browser back
 * to the API, which sets the cookie and bounces to `next`. XHR cannot follow
 * that, and the cookie would be set on a response nobody is looking at.
 */
export function oauthUrl(provider: 'github' | 'google', next = '/'): string {
  return `${API_BASE}/auth/${provider}/start?next=${encodeURIComponent(next)}`
}
