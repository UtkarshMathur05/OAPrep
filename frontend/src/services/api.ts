// The only place the frontend talks to the backend.
// With VITE_USE_MOCK=true every call resolves from data/mockData.ts instead,
// so the UI can be built before the backend exists.

import axios from 'axios'
import type {
  ProblemDetail, ProblemListParams, ProblemListResponse,
  MemoryRequest, MemoryResponse,
  SearchRequest, SearchResponse,
  ReconstructRequest, ReconstructResponse,
  VerifyRequest, VerifyResponse,
} from '../types'
import {
  mockMemoryResponse, mockSearchResponse, mockReconstructResponse, mockVerifyResponse,
  mockProblemList, mockProblemDetail,
} from '../data/mockData'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
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
