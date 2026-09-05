import { useState, useEffect } from 'react'
import type { Candidate, Genome, Problem, VerifyResponse } from '../types'
import { extractMemory, searchCandidates, reconstructProblem, verifySolution } from '../services/api'
import VoiceRecorder from '../components/VoiceRecorder'
import MemoryCard from '../components/MemoryCard'
import CandidateList from '../components/CandidateList'
import ProblemDisplay from '../components/ProblemDisplay'
import CodeEditor from '../components/CodeEditor'
import TestResults from '../components/TestResults'

type Step = 'input' | 'memory' | 'candidates' | 'problem'

interface RecallState {
  step: Step
  transcript: string
  memoryId: string | null
  memory: Genome | null
  candidates: Candidate[]
  selected: Candidate | null
  problem: Problem | null
  code: string
  result: VerifyResponse | null
  loading: boolean
  error: string | null
}

const STEPS: { id: Step; label: string }[] = [
  { id: 'input', label: 'Recall' },
  { id: 'memory', label: 'Analysis' },
  { id: 'candidates', label: 'Matches' },
  { id: 'problem', label: 'Solve' },
]

export default function Reconstruct() {
  const [state, setState] = useState<RecallState>({
    step: 'input',
    transcript: '',
    memoryId: null,
    memory: null,
    candidates: [],
    selected: null,
    problem: null,
    code: '',
    result: null,
    loading: false,
    error: null,
  })

  const handleInputSubmit = async (transcript: string) => {
    setState(s => ({ ...s, loading: true, error: null, transcript }))
    try {
      const res = await extractMemory({ transcript })
      setState(s => ({
        ...s,
        loading: false,
        memoryId: res.memory_id,
        memory: res.memory,
        step: 'memory'
      }))
    } catch (err) {
      setState(s => ({ ...s, loading: false, error: 'We couldn\'t process your memory. Please try again or add more details.' }))
    }
  }

  const handleSearchCandidates = async () => {
    if (!state.memory) return
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const res = await searchCandidates({ memory: state.memory, memory_id: state.memoryId || undefined })
      setState(s => ({
        ...s,
        loading: false,
        candidates: res.candidates,
        step: 'candidates'
      }))
    } catch (err) {
      setState(s => ({ ...s, loading: false, error: 'Failed to find matching candidates. Please try again.' }))
    }
  }

  const handleSelectCandidate = async (candidate: Candidate) => {
    if (!state.memoryId) return
    setState(s => ({ ...s, loading: true, error: null, selected: candidate }))
    try {
      const res = await reconstructProblem({ memory_id: state.memoryId, candidate_id: candidate.id })
      setState(s => ({
        ...s,
        loading: false,
        problem: res.problem,
        code: res.problem.starter_code || '',
        step: 'problem'
      }))
    } catch (err) {
      setState(s => ({ ...s, loading: false, error: 'Failed to reconstruct the problem.' }))
    }
  }

  const handleVerify = async () => {
    if (!state.problem || !state.problem.id) return
    setState(s => ({ ...s, loading: true, error: null, result: null }))
    try {
      const res = await verifySolution({ problem_id: state.problem.id, code: state.code, language: 'python' })
      setState(s => ({ ...s, loading: false, result: res }))
    } catch (err) {
      setState(s => ({ ...s, loading: false, error: 'Verification failed.' }))
    }
  }

  const currentStepIndex = STEPS.findIndex(s => s.id === state.step)

  return (
    <div className="mx-auto grid max-w-6xl gap-8 px-5 py-8 lg:grid-cols-[13rem_1fr]">
      {/* Step rail. The flow really is a sequence, so it is numbered. */}
      <nav aria-label="Progress" className="lg:sticky lg:top-16 lg:self-start">
        <ol className="flex gap-4 lg:block lg:space-y-0">
          {STEPS.map((stepItem, idx) => {
            const isActive = idx === currentStepIndex
            const isPast = idx < currentStepIndex
            return (
              <li
                key={stepItem.id}
                aria-current={isActive ? 'step' : undefined}
                className={`flex items-baseline gap-2.5 border-l-2 py-1.5 pl-3 transition-colors
                  ${isActive ? 'border-brownRed text-prussianBlue'
                    : isPast ? 'border-ruleStrong text-shadowGrey'
                    : 'border-rule text-muted'}`}
              >
                <span className="font-mono text-2xs tabular-nums">{idx + 1}</span>
                <span className={`text-sm ${isActive ? 'font-medium' : ''}`}>{stepItem.label}</span>
              </li>
            )
          })}
        </ol>
      </nav>

      <main className="min-w-0">
        {state.error && (
          <div role="alert" className="mb-6 border border-brownRed/30 border-l-2 border-l-brownRed bg-brownRed/5 px-4 py-3">
            <p className="text-sm text-brownRed">{state.error}</p>
          </div>
        )}

        {state.step === 'input' && (
          <div className="max-w-reading">
            <h2 className="mb-3 text-3xl font-semibold tracking-tight">What do you remember?</h2>
            <p className="mb-6 text-shadowGrey">
              Anything counts — the shape of the input, what you had to return, a
              constraint that stuck. Say what you are unsure about too; it is kept
              separate rather than used to narrow the search.
            </p>
            <VoiceRecorder onSubmit={handleInputSubmit} loading={state.loading} />
          </div>
        )}

        {state.step === 'memory' && state.memory && (
          <div className="max-w-3xl">
            <h2 className="mb-1 text-2xl font-semibold tracking-tight">Here is what came through</h2>
            <p className="mb-5 text-shadowGrey">Check it before we search 1,124 problems.</p>
            <MemoryCard memory={state.memory} />
            <div className="mt-5 flex justify-end">
              <button
                className="bg-prussianBlue px-5 py-2.5 font-medium text-floralWhite transition-colors
                           hover:bg-shadowGrey disabled:opacity-50
                           focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brownRed"
                onClick={handleSearchCandidates}
                disabled={state.loading}
              >
                {state.loading ? 'Searching…' : 'Find matches'}
              </button>
            </div>
          </div>
        )}

        {state.step === 'candidates' && (
          <div>
            <h2 className="mb-1 text-2xl font-semibold tracking-tight">Closest matches</h2>
            <p className="mb-5 text-shadowGrey">
              Ranked by how well each explains what you remember. Pick the one that clicks.
            </p>
            {state.loading
              ? <p className="border border-rule bg-surface p-6 text-muted">Searching the corpus…</p>
              : <CandidateList candidates={state.candidates} onSelect={handleSelectCandidate} />}
          </div>
        )}

        {state.step === 'problem' && state.problem && (
          <div className="grid gap-6 xl:grid-cols-2">
            <ProblemDisplay problem={state.problem} />
            <div className="flex min-w-0 flex-col gap-4">
              <div className="border border-ruleStrong bg-surface">
                <div className="flex items-center justify-between border-b border-ruleStrong px-4 py-2">
                  <span className="font-mono text-sm text-muted">solution.py</span>
                  <button
                    onClick={handleVerify}
                    disabled={state.loading}
                    className="border border-prussianBlue px-3 py-1 text-sm font-medium transition-colors
                               hover:bg-prussianBlue hover:text-floralWhite disabled:opacity-50
                               focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brownRed"
                  >
                    {state.loading ? 'Running…' : 'Run tests'}
                  </button>
                </div>
                <CodeEditor
                  value={state.code}
                  language="python"
                  onChange={v => setState(s => ({ ...s, code: v }))}
                />
              </div>
              {state.result && <TestResults result={state.result} />}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
