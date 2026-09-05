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
    <main className="max-w-5xl mx-auto px-6 py-12">
      {/* Stepper */}
      <nav className="mb-12">
        <ul className="flex items-center gap-4">
          {STEPS.map((stepItem, idx) => {
            const isActive = idx === currentStepIndex
            const isPast = idx < currentStepIndex
            return (
              <li key={stepItem.id} className="flex items-center gap-4">
                <div className={`flex items-center gap-2 text-sm font-medium transition-colors ${isActive ? 'text-brownRed' : isPast ? 'text-prussianBlue' : 'text-shadowGrey/40'}`}>
                  <span className={`w-6 h-6 flex items-center justify-center border-2 rounded-sm ${isActive ? 'border-brownRed bg-brownRed/10' : isPast ? 'border-prussianBlue bg-prussianBlue text-floralWhite' : 'border-shadowGrey/30'}`}>
                    {isPast ? '✓' : idx + 1}
                  </span>
                  {stepItem.label}
                </div>
                {idx < STEPS.length - 1 && (
                  <div className={`w-8 h-[2px] ${isPast ? 'bg-prussianBlue' : 'bg-shadowGrey/20'}`} />
                )}
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Error */}
      {state.error && (
        <div className="mb-8 p-4 border-l-4 border-brownRed bg-brownRed/10 text-brownRed font-medium">
          {state.error}
        </div>
      )}

      {/* Content */}
      <div className="min-h-[400px]">
        {state.step === 'input' && (
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight mb-4 text-prussianBlue">What do you remember?</h2>
            <p className="text-shadowGrey mb-8 text-lg">Describe any fragments of the coding problem you recall. Mention constraints, data structures, or even just the premise.</p>
            <VoiceRecorder onSubmit={handleInputSubmit} loading={state.loading} />
          </div>
        )}

        {state.step === 'memory' && state.memory && (
          <div className="max-w-3xl">
            <h2 className="text-2xl font-bold mb-6">Memory Analysis</h2>
            <MemoryCard memory={state.memory} />
            <div className="mt-8 flex justify-end">
              <button
                className="bg-prussianBlue text-floralWhite px-6 py-3 font-semibold disabled:opacity-50 hover:bg-shadowGrey transition-colors"
                onClick={handleSearchCandidates}
                disabled={state.loading}
              >
                {state.loading ? 'Searching...' : 'Find Matches →'}
              </button>
            </div>
          </div>
        )}

        {state.step === 'candidates' && (
          <div className="max-w-3xl">
            <h2 className="text-2xl font-bold mb-2">Matching Candidates</h2>
            <p className="text-shadowGrey mb-8">We found these problems based on your memory. Select the one that seems correct.</p>
            {state.loading ? (
              <div className="text-shadowGrey font-medium animate-pulse">Loading candidates...</div>
            ) : (
              <CandidateList candidates={state.candidates} onSelect={handleSelectCandidate} />
            )}
          </div>
        )}

        {state.step === 'problem' && state.problem && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            <div>
              <ProblemDisplay problem={state.problem} />
            </div>
            <div className="flex flex-col gap-6">
              <div className="border border-shadowGrey/20 bg-white">
                <div className="bg-prussianBlue text-floralWhite px-4 py-2 text-sm font-medium flex justify-between items-center">
                  <span>solution.py</span>
                  <button 
                    onClick={handleVerify} 
                    disabled={state.loading}
                    className="bg-amberEarth text-prussianBlue px-3 py-1 text-xs font-bold uppercase tracking-wider hover:bg-amberEarth/90 disabled:opacity-50"
                  >
                    {state.loading ? 'Running...' : 'Run Tests'}
                  </button>
                </div>
                <CodeEditor value={state.code} language="python" onChange={v => setState(s => ({ ...s, code: v }))} />
              </div>
              {state.result && <TestResults result={state.result} />}
            </div>
          </div>
        )}
      </div>
    </main>
  )
}

