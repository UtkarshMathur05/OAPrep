import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import type { Candidate, Genome, Problem } from '../types'
import { extractMemory, searchCandidates, reconstructProblem } from '../services/api'
import VoiceRecorder from '../components/VoiceRecorder'
import MemoryCard, { UncertaintyPanel } from '../components/MemoryCard'
import CandidateList from '../components/CandidateList'
import ProblemDisplay from '../components/ProblemDisplay'

type Step = 'input' | 'memory' | 'candidates' | 'problem'

/** Memories that actually resolve — the same set the landing hero offers, so
 *  arriving here directly is not a blank page. */
const EXAMPLES = [
  {
    chip: 'a triangle of numbers',
    text: 'It was a triangle of numbers and you walked down it row by row, only to the number below or the one next to it, and you wanted the cheapest path to the bottom.',
  },
  {
    chip: 'a grid, right or down',
    text: 'There was a grid where you could only move right or down and you had to make some total as small as possible. I think there were obstacles?',
  },
  {
    chip: 'bars holding rainwater',
    text: 'Something with bars of different heights and working out how much rain would sit between them after it stopped.',
  },
]

const STEPS: { id: Step; label: string }[] = [
  { id: 'input', label: 'memory' },
  { id: 'memory', label: 'genome' },
  { id: 'candidates', label: 'matches' },
  { id: 'problem', label: 'problem' },
]

interface RecallState {
  step: Step
  transcript: string
  memoryId: string | null
  memory: Genome | null
  candidates: Candidate[]
  selected: Candidate | null
  problem: Problem | null
  loading: boolean
  error: string | null
}

const EMPTY: RecallState = {
  step: 'input', transcript: '', memoryId: null, memory: null,
  candidates: [], selected: null, problem: null, loading: false, error: null,
}

/**
 * The recall flow, as one console rather than four pages.
 *
 * Laid out as separate full-page steps this read as a sparse form: a heading, a
 * field, and a great deal of nothing. It is the product's whole differentiator,
 * so it should feel like a single instrument you are watching transform state —
 * bounded panel, progress in its header, and the memory you typed pinned at the
 * top the entire way down, because every later screen is an answer to it.
 */
export default function Reconstruct() {
  const navigate = useNavigate()
  const location = useLocation()
  const [state, setState] = useState<RecallState>(EMPTY)
  const [seed, setSeed] = useState('')

  const set = (patch: Partial<RecallState>) => setState((s) => ({ ...s, ...patch }))

  const handleInputSubmit = async (transcript: string) => {
    set({ loading: true, error: null, transcript })
    try {
      const res = await extractMemory({ transcript })
      set({ loading: false, memoryId: res.memory_id, memory: res.memory, step: 'memory' })
    } catch {
      set({ loading: false, error: "We couldn't read that memory. Try again, or add another detail." })
    }
  }

  const handleSearchCandidates = async () => {
    if (!state.memory) return
    set({ loading: true, error: null })
    try {
      const res = await searchCandidates({
        memory: state.memory,
        memory_id: state.memoryId || undefined,
      })
      set({ loading: false, candidates: res.candidates, step: 'candidates' })
    } catch {
      set({ loading: false, error: 'Nothing came back from the corpus. Try adding another detail.' })
    }
  }

  const handleSelectCandidate = async (candidate: Candidate) => {
    if (!state.memoryId) return
    set({ loading: true, error: null, selected: candidate, step: 'problem' })
    try {
      const res = await reconstructProblem({
        memory_id: state.memoryId,
        candidate_id: candidate.id,
      })
      set({ loading: false, problem: res.problem })
    } catch {
      set({ loading: false, error: 'Failed to rebuild that problem.', step: 'candidates' })
    }
  }

  // The landing page's hero submits straight into this flow.
  const handed = (location.state as { transcript?: string } | null)?.transcript
  const started = useRef(false)
  useEffect(() => {
    if (handed && !started.current) {
      started.current = true
      handleInputSubmit(handed)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handed])

  const current = STEPS.findIndex((s) => s.id === state.step)
  const showEcho = state.step !== 'input' && state.transcript

  return (
    <div className="shell py-10">
      <div className="mx-auto max-w-5xl">
        <div className="border border-lineStrong bg-panel">
          {/* Header: what this is, and how far through it you are. */}
          <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-lineStrong px-5 py-3">
            <span className="font-mono text-small font-semibold">recall</span>
            <ol className="flex items-center gap-1">
              {STEPS.map((s, i) => (
                <li key={s.id} className="flex items-center gap-1">
                  {i > 0 && (
                    <span
                      aria-hidden
                      className={`mx-1 h-px w-5 ${i <= current ? 'bg-lineStrong' : 'bg-line'}`}
                    />
                  )}
                  <span
                    aria-current={i === current ? 'step' : undefined}
                    className={`font-mono text-micro ${
                      i === current ? 'text-accent'
                      : i < current ? 'text-ink2'
                      : 'text-ink3'}`}
                  >
                    <span className="num">{String(i + 1).padStart(2, '0')}</span> {s.label}
                  </span>
                </li>
              ))}
            </ol>
          </div>

          {/* The memory, pinned. Every screen below is an answer to this line,
              and losing sight of it is what made the later steps feel unmoored. */}
          {showEcho && (
            <div className="flex items-start gap-3 border-b border-line bg-ground px-5 py-3">
              <span aria-hidden className="select-none font-mono text-small text-accent">&gt;</span>
              <p className="min-w-0 flex-1 font-mono text-small leading-relaxed text-ink2">
                {state.transcript}
              </p>
              <button
                onClick={() => setState({ ...EMPTY })}
                className="shrink-0 font-mono text-micro text-ink3 link hover:text-ink"
              >
                start over
              </button>
            </div>
          )}

          {state.error && (
            <div role="alert" className="border-b border-line border-l-2 border-l-brownRed bg-accent/5 px-5 py-3">
              <p className="text-small text-hard">{state.error}</p>
            </div>
          )}

          <div className="p-5 sm:p-7">
            {state.step === 'input' && (
              <div className="animate-rise">
                <h1 className="text-h2">What do you remember?</h1>
                <p className="mt-1.5 max-w-reading text-small text-ink2">
                  Anything counts — the shape of the input, what you had to return,
                  a constraint that stuck. Say what you are unsure about too: it is
                  kept out of the search rather than used to narrow it.
                </p>
                <div className="mt-5">
                  <VoiceRecorder onSubmit={handleInputSubmit} loading={state.loading} seed={seed} />
                </div>
                <div className="mt-4 flex flex-wrap items-baseline gap-2">
                  <span className="label">or try</span>
                  {EXAMPLES.map((ex) => (
                    <button key={ex.chip} onClick={() => setSeed(ex.text)} className="chip">
                      {ex.chip}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {state.step === 'memory' && state.memory && (
              <div className="animate-rise">
                <h2 className="text-h3">Here is what came through</h2>
                <p className="mt-1.5 text-small text-ink2">
                  Check it before we search. Only the left column becomes the query.
                </p>
                {/* Side by side on purpose: "we keep uncertainty separate" is a
                    claim, and this is the layout that shows it rather than
                    saying it in a caption. */}
                <div className="mt-5 grid items-start gap-5 lg:grid-cols-[1.35fr_1fr]">
                  <MemoryCard memory={state.memory} ledgerOnly />
                  <UncertaintyPanel items={state.memory.uncertainties ?? []} />
                </div>
                <div className="mt-6 flex items-center justify-between gap-4 border-t border-line pt-5">
                  <p className="font-mono text-micro text-ink3">
                    next: vector search over 1,124 statements, then a rerank
                  </p>
                  <button className="btn-accent" onClick={handleSearchCandidates} disabled={state.loading}>
                    {state.loading ? 'searching…' : 'find matches'}
                  </button>
                </div>
              </div>
            )}

            {state.step === 'candidates' && (
              <div className="animate-rise">
                <h2 className="text-h3">Closest matches</h2>
                <p className="mt-1.5 text-small text-ink2">
                  Ranked by how well each one explains what you remember, not by
                  raw text similarity. Pick the one that clicks.
                </p>
                <div className="mt-5">
                  {state.loading
                    ? <Waiting label="searching the corpus…" />
                    : <CandidateList candidates={state.candidates} onSelect={handleSelectCandidate} />}
                </div>
                <div className="mt-6 flex items-center justify-between gap-4 border-t border-line pt-5">
                  <button
                    onClick={() => set({ step: 'memory' })}
                    className="font-mono text-micro text-ink2 link"
                  >
                    back to the genome
                  </button>
                  <p className="font-mono text-micro text-ink3">
                    none of these? <a href="/contribute" className="text-link link">add it</a>
                  </p>
                </div>
              </div>
            )}

            {state.step === 'problem' && (
              <div className="animate-rise">
                {state.loading || !state.problem ? (
                  <Waiting label={`rebuilding ${state.selected?.title ?? 'the problem'}…`} />
                ) : (
                  <>
                    <ProblemDisplay problem={state.problem} />
                    <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5">
                      <button
                        onClick={() => set({ step: 'candidates', problem: null })}
                        className="font-mono text-micro text-ink2 link"
                      >
                        try a different match
                      </button>
                      {state.problem.solvable === false ? (
                        /* Rebuilding it worked; running it never can. Offering
                           the editor here and failing at Run would waste the
                           attempt and explain nothing. */
                        <div className="flex flex-wrap items-center gap-4">
                          <span className="max-w-reading font-mono text-micro leading-relaxed text-ink3">
                            {state.problem.unsolvable_reason}
                          </span>
                          {state.problem.source_url && (
                            <a
                              href={state.problem.source_url}
                              target="_blank"
                              rel="noreferrer noopener"
                              className="btn-accent"
                            >
                              solve on LeetCode
                            </a>
                          )}
                        </div>
                      ) : (
                        <div className="flex items-center gap-4">
                          <span className="font-mono text-micro text-ink3">
                            run against real test cases
                          </span>
                          <button
                            onClick={() =>
                              navigate(`/solve/${state.problem!.id ?? ''}`, {
                                state: { problem: state.problem },
                              })
                            }
                            className="btn-accent"
                          >
                            open the editor
                          </button>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/** A waiting state with a real height, so the panel does not collapse and
 *  jump the page while a Gemini call is in flight. */
function Waiting({ label }: { label: string }) {
  return (
    <div className="flex h-40 items-center justify-center border border-line bg-ground">
      <span className="font-mono text-small text-ink2">
        {label}
        <span className="ml-1 inline-block animate-pulse text-accent">▌</span>
      </span>
    </div>
  )
}
