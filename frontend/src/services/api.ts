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
} from '../types'
import {
  mockMemoryResponse, mockSearchResponse, mockReconstructResponse, mockVerifyResponse,
  mockProblemList, mockProblemDetail, mockFacets,
} from '../data/mockData'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Every request carries the session, so no call site has to remember to. When
// real auth lands this interceptor is where the token goes instead.
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
