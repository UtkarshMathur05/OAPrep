import { useState } from 'react'
import { Link } from 'react-router-dom'
import type {
  Candidate, ContributeDetails, ContributeResponse, Genome,
} from '../types'
import { matchContribution, submitContribution } from '../services/api'
import MemoryCard from '../components/MemoryCard'

type Step = 'describe' | 'match' | 'details' | 'done'

const EMPTY: ContributeDetails = {
  title: '', difficulty: '', topics: [], companies: [],
  input_format: '', output_format: '', example: '', constraints: '',
}

/**
 * Contributing runs the recall pipeline first, on purpose.
 *
 * The failure mode of any "add a problem" form is fifty slightly different
 * copies of Two Sum. We already have the machinery to notice that, so a
 * contribution starts as a search: if the corpus has it, the user's account
 * becomes corroboration instead of a duplicate row.
 */
export default function Contribute() {
  const [step, setStep] = useState<Step>('describe')
  const [transcript, setTranscript] = useState('')
  const [memory, setMemory] = useState<Genome | null>(null)
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [likelyDuplicate, setLikelyDuplicate] = useState(false)
  const [details, setDetails] = useState<ContributeDetails>(EMPTY)
  const [result, setResult] = useState<ContributeResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runMatch = async () => {
    setBusy(true); setError(null)
    try {
      const res = await matchContribution({ transcript: transcript.trim() })
      setMemory(res.memory)
      setCandidates(res.candidates)
      setLikelyDuplicate(res.likely_duplicate)
      setStep('match')
    } catch {
      setError('We could not check that against the corpus. Is the backend running with a Gemini key?')
    } finally {
      setBusy(false)
    }
  }

  const send = async (confirmId?: string) => {
    setBusy(true); setError(null)
    try {
      setResult(await submitContribution({
        transcript: transcript.trim(),
        details,
        confirm_problem_id: confirmId,
      }))
      setStep('done')
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Could not save that. Try again in a moment.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="shell py-12">
      <div className="max-w-3xl">
      <h1 className="text-h1">Add a problem we're missing</h1>
      <p className="mt-3 max-w-reading text-lede text-shadowGrey">
        Describe it the same way you would in recall. We check the corpus first —
        if we already have it, your description raises that problem's confidence
        instead of creating a near-duplicate.
      </p>

      {error && (
        <p role="alert" className="mt-6 border border-hard/30 border-l-2 border-l-hard bg-hard/5 px-4 py-3 text-small text-hard">
          {error}
        </p>
      )}

      {step === 'describe' && (
        <div className="mt-8 animate-rise">
          <label htmlFor="desc" className="label">what was the problem?</label>
          <textarea
            id="desc"
            rows={6}
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="you were given a list of tasks with cooldowns and had to schedule them so the total time was minimal…"
            className="mt-2 w-full resize-y border border-prussianBlue bg-surface px-4 py-3 text-base leading-relaxed
                       placeholder:text-faint focus:outline-none"
          />
          <div className="mt-3 flex items-center justify-between gap-4">
            <p className="font-mono text-micro text-faint">
              {transcript.trim().length < 20 ? 'a sentence or two, at least' : ' '}
            </p>
            <button onClick={runMatch} disabled={busy || transcript.trim().length < 20} className="btn-accent">
              {busy ? 'checking the corpus…' : 'check if we have it'}
            </button>
          </div>
        </div>
      )}

      {step === 'match' && (
        <div className="mt-8 animate-rise">
          {memory && (
            <>
              <h2 className="mb-2 label">what we read from that</h2>
              <MemoryCard memory={memory} />
            </>
          )}

          <h2 className="mb-2 mt-8 label">
            {candidates.length ? 'is it one of these?' : 'nothing in the corpus looks like it'}
          </h2>

          {likelyDuplicate && (
            <p className="mb-3 border border-amberEarth/40 border-l-2 border-l-amberEarth bg-amberEarth/10 px-4 py-2.5 text-small text-shadowGrey">
              The top match is close enough that this is probably the same problem.
            </p>
          )}

          <ul className="divide-y divide-rule border border-rule bg-surface">
            {candidates.map((c, i) => (
              <li key={c.id} className="flex items-baseline gap-4 px-4 py-3">
                <span className="num w-12 shrink-0 font-mono text-small text-muted">
                  {Math.round(c.confidence * 100)}%
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{c.title}</p>
                  {c.reason && <p className="mt-0.5 text-small text-muted">{c.reason}</p>}
                </div>
                {/* When retrieval is confident, confirming is the right action,
                    so it gets the emphasis — not "add it anyway". */}
                <button
                  onClick={() => send(c.id)}
                  disabled={busy}
                  className={`shrink-0 ${likelyDuplicate && i === 0 ? 'btn-primary' : 'btn-ghost'}`}
                >
                  that's it
                </button>
              </li>
            ))}
            {!candidates.length && (
              <li className="px-4 py-5 text-small text-muted">
                No candidate came back above the retrieval threshold. That is a good
                sign for contributing.
              </li>
            )}
          </ul>

          <div className="mt-5 flex items-center justify-between">
            <button onClick={() => setStep('describe')} className="font-mono text-micro text-muted link">
              edit my description
            </button>
            <button
              onClick={() => setStep('details')}
              className={likelyDuplicate ? 'btn-ghost' : 'btn-accent'}
            >
              none of these — add it
            </button>
          </div>
        </div>
      )}

      {step === 'details' && (
        <div className="mt-8 animate-rise">
          <h2 className="text-h3">A few more details</h2>
          <p className="mt-1.5 max-w-reading text-small text-muted">
            All optional. Anything you leave blank gets inferred when we write the
            statement up, and every inference is listed on the problem page rather
            than presented as fact.
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <Field label="Title you'd give it" value={details.title!}
                   onChange={(v) => setDetails({ ...details, title: v })}
                   placeholder="Task scheduler with cooldown" />
            <div>
              <label className="label" htmlFor="difficulty">difficulty</label>
              <select
                id="difficulty"
                value={details.difficulty}
                onChange={(e) => setDetails({ ...details, difficulty: e.target.value })}
                className="field mt-1.5"
              >
                <option value="">Not sure</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            <ListField label="Topics" values={details.topics!} placeholder="Greedy, Hash Table"
                       onChange={(v) => setDetails({ ...details, topics: v })} />
            <ListField label="Where it was asked" values={details.companies!} placeholder="google, zoho"
                       onChange={(v) => setDetails({ ...details, companies: v })} />
            <Field label="Input format" value={details.input_format!}
                   onChange={(v) => setDetails({ ...details, input_format: v })}
                   placeholder="First line n, then n integers" />
            <Field label="Output format" value={details.output_format!}
                   onChange={(v) => setDetails({ ...details, output_format: v })}
                   placeholder="A single integer" />
          </div>

          <div className="mt-4 grid gap-4">
            <Field label="An example you remember" value={details.example!} textarea
                   onChange={(v) => setDetails({ ...details, example: v })}
                   placeholder={'Input: 6\\n1 2 1 2 3 3\\nOutput: 8'} />
            <Field label="Constraints" value={details.constraints!}
                   onChange={(v) => setDetails({ ...details, constraints: v })}
                   placeholder="n up to 10^5" />
          </div>

          <div className="mt-6 flex items-center justify-between">
            <button onClick={() => setStep('match')} className="font-mono text-micro text-muted link">
              back to matches
            </button>
            <button onClick={() => send()} disabled={busy} className="btn-primary">
              {busy ? 'writing it up…' : 'add to the corpus'}
            </button>
          </div>
        </div>
      )}

      {step === 'done' && result && (
        <div className="mt-8 animate-rise border border-ruleStrong bg-surface p-6">
          <p className="label">{result.action === 'created' ? 'added' : 'corroborated'}</p>
          <h2 className="mt-1 text-h2">{result.title}</h2>
          <p className="mt-3 max-w-reading text-small text-shadowGrey">{result.message}</p>

          <div className="mt-5 flex items-baseline gap-6 border-y border-rule py-4">
            <Stat label="Confidence" value={`${Math.round(result.confidence * 100)}%`} />
            <Stat label="Descriptions" value={String(result.contribution_count)} />
            <Stat label="Test cases" value={String(result.test_case_count)} />
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Link to={`/problems/${result.slug}`} className="btn-primary">see the problem</Link>
            <Link to={`/solve/${result.slug}`} className="btn-ghost">solve it</Link>
            <button
              onClick={() => {
                setStep('describe'); setTranscript(''); setDetails(EMPTY)
                setResult(null); setCandidates([]); setMemory(null)
              }}
              className="btn-ghost"
            >
              add another
            </button>
          </div>
        </div>
      )}
      </div>
    </div>
  )
}

function Field({
  label, value, onChange, placeholder, textarea,
}: {
  label: string; value: string; onChange: (v: string) => void
  placeholder?: string; textarea?: boolean
}) {
  const cls = 'field mt-1.5'
  return (
    <div>
      <label className="label">{label}</label>
      {textarea ? (
        <textarea rows={3} value={value} placeholder={placeholder}
                  onChange={(e) => onChange(e.target.value)} className={`${cls} resize-y font-mono`} />
      ) : (
        <input value={value} placeholder={placeholder}
               onChange={(e) => onChange(e.target.value)} className={cls} />
      )}
    </div>
  )
}

/** Comma-separated in, array out. A tag widget would be nicer and is not the
 *  difference between this working and not. */
function ListField({
  label, values, onChange, placeholder,
}: { label: string; values: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  return (
    <Field
      label={label}
      value={values.join(', ')}
      placeholder={placeholder}
      onChange={(v) => onChange(v.split(',').map((s) => s.trim()).filter(Boolean))}
    />
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="num font-mono text-h3">{value}</p>
      <p className="label">{label}</p>
    </div>
  )
}