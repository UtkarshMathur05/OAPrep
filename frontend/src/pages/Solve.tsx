import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import type { Problem, ProblemDetail, VerifyResponse } from '../types'
import { getProblem, verifySolution } from '../services/api'
import Timer from '../components/Timer'

const STARTER = `import sys

def main():
    data = sys.stdin.read().split()
    # your solution here
    print(0)

if __name__ == "__main__":
    main()
`

/**
 * The solve environment.
 *
 * Full-bleed and dark, outside the site shell: once you are writing code the
 * site's navigation is a distraction, and the only bright thing on the display
 * should be the code. Statement left, editor right, results under the editor —
 * the layout every online judge uses, because it is the one where you can read
 * the failing input without losing your place in the code.
 */
export default function Solve() {
  const { slug = '' } = useParams()
  const location = useLocation()

  // The recall flow hands its reconstructed problem over in router state, so
  // the user solves the statement they were just shown rather than the corpus
  // row it was rebuilt from.
  const handed = (location.state as { problem?: Problem } | null)?.problem ?? null

  const [problem, setProblem] = useState<ProblemDetail | Problem | null>(handed)
  const [code, setCode] = useState(handed?.starter_code || STARTER)
  const [result, setResult] = useState<VerifyResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [split, setSplit] = useState(42)

  useEffect(() => {
    if (handed) return
    getProblem(slug)
      .then((p) => setProblem(p))
      .catch(() => setError('We could not load that problem.'))
  }, [slug, handed])

  const problemId = (problem as ProblemDetail | null)?.id ?? handed?.id ?? null

  const run = useCallback(async () => {
    if (!problemId) return
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      setResult(await verifySolution({ problem_id: problemId, code, language: 'python' }))
    } catch {
      setError('The run did not come back. Judge0 may be rate-limited — try again in a moment.')
    } finally {
      setRunning(false)
    }
  }, [problemId, code])

  // ⌘↵ runs, the way every judge does it.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        run()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [run])

  const dragging = useRef(false)
  useEffect(() => {
    const move = (e: MouseEvent) => {
      if (!dragging.current) return
      setSplit(Math.min(70, Math.max(24, (e.clientX / window.innerWidth) * 100)))
    }
    const up = () => { dragging.current = false; document.body.style.cursor = '' }
    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', up)
    return () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up) }
  }, [])

  return (
    <div className="flex h-screen flex-col bg-deep text-white/90">
      <header className="flex shrink-0 items-center gap-4 border-b border-deepRule px-4 py-2.5">
        <Link to={problem && 'slug' in problem ? `/problems/${problem.slug}` : '/problems'}
              className="text-sm text-white/50 transition-colors hover:text-white">
          ← Back
        </Link>
        <span className="truncate font-medium">{problem?.title ?? 'Loading…'}</span>

        <div className="ml-auto flex items-center gap-4">
          <Timer />
          <span className="font-mono text-micro text-white/40">Python 3</span>
          <button onClick={run} disabled={running || !problemId}
                  className="btn bg-amberEarth px-4 text-deep hover:bg-amberEarth/90">
            {running ? 'Running…' : 'Run tests'}
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Statement */}
        <section style={{ width: `${split}%` }}
                 className="min-w-0 overflow-y-auto border-r border-deepRule px-6 py-5">
          {error && !problem && <p role="alert" className="text-hard">{error}</p>}
          {problem && (
            <>
              <h1 className="text-xl font-semibold tracking-tight">{problem.title}</h1>
              <div className="mt-4 max-w-reading whitespace-pre-wrap text-sm leading-relaxed text-white/70">
                {problem.description}
              </div>

              {'constraints' in problem && problem.constraints?.length > 0 && (
                <>
                  <h2 className="mt-6 text-sm font-medium">Constraints</h2>
                  <ul className="mt-2 space-y-1 font-mono text-micro text-white/60">
                    {problem.constraints.map((c) => <li key={c}>{c}</li>)}
                  </ul>
                </>
              )}

              {'examples' in problem && problem.examples?.length > 0 && (
                <>
                  <h2 className="mt-6 text-sm font-medium">Examples</h2>
                  <div className="mt-2 space-y-3">
                    {problem.examples.map((ex, i) => (
                      <div key={i} className="border border-deepRule bg-deepPanel p-3 font-mono text-micro">
                        <p className="text-white/40">Input</p>
                        <pre className="mt-1 whitespace-pre-wrap text-white/80">{ex.input}</pre>
                        <p className="mt-2 text-white/40">Output</p>
                        <pre className="mt-1 whitespace-pre-wrap text-white/80">{ex.output}</pre>
                        {ex.explanation && <p className="mt-2 text-white/50">{ex.explanation}</p>}
                      </div>
                    ))}
                  </div>
                </>
              )}

              <p className="mt-8 border-t border-deepRule pt-4 text-micro text-white/40">
                Your program reads the whole of stdin and prints the answer to
                stdout. Test inputs are given exactly as shown above.
              </p>
            </>
          )}
        </section>

        <div
          role="separator"
          aria-orientation="vertical"
          onMouseDown={() => { dragging.current = true; document.body.style.cursor = 'col-resize' }}
          className="w-1 shrink-0 cursor-col-resize bg-deepRule transition-colors hover:bg-amberEarth"
        />

        {/* Editor + console */}
        <section className="flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-1">
            <Editor
              height="100%"
              language="python"
              value={code}
              theme="vs-dark"
              onChange={(v) => setCode(v ?? '')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                padding: { top: 16, bottom: 16 },
                scrollBeyondLastLine: false,
                smoothScrolling: true,
                renderLineHighlight: 'gutter',
                overviewRulerBorder: false,
              }}
            />
          </div>
          <Console result={result} running={running} error={error} />
        </section>
      </div>
    </div>
  )
}

function Console({
  result, running, error,
}: { result: VerifyResponse | null; running: boolean; error: string | null }) {
  const [open, setOpen] = useState(true)
  const passed = result ? result.passed === result.total && result.total > 0 : false
  const failing = result?.results?.find((r) => !r.passed)

  return (
    <div className="shrink-0 border-t border-deepRule bg-deepPanel">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-4 py-2 text-left"
      >
        <span className="text-sm">Results</span>
        {running && <span className="font-mono text-micro text-amberEarth">running…</span>}
        {result && (
          <>
            <span className={`text-sm font-medium ${passed ? 'text-easy' : 'text-hard'}`}>
              {passed ? 'Accepted' : result.status}
            </span>
            <span className="num font-mono text-micro text-white/50">
              {result.passed}/{result.total} passed
              {result.runtime && ` · ${result.runtime}`}
              {result.memory && ` · ${result.memory}`}
            </span>
          </>
        )}
        <span className="ml-auto text-micro text-white/40">{open ? 'Hide' : 'Show'}</span>
      </button>

      {open && (
        <div className="max-h-56 overflow-y-auto border-t border-deepRule px-4 py-3">
          {error && <p role="alert" className="text-sm text-hard">{error}</p>}

          {!result && !running && !error && (
            <p className="text-sm text-white/40">
              Run your solution to see how it does against the stored test cases.
              <span className="ml-2 font-mono text-micro">⌘↵</span>
            </p>
          )}

          {result && (
            <>
              <div className="flex flex-wrap gap-1.5">
                {result.results.map((r) => (
                  <span
                    key={r.index}
                    title={`Case ${r.index + 1}: ${r.passed ? 'passed' : 'failed'}`}
                    className={`num flex h-6 w-6 items-center justify-center font-mono text-micro
                      ${r.passed ? 'bg-easy/20 text-easy' : 'bg-hard/20 text-hard'}`}
                  >
                    {r.index + 1}
                  </span>
                ))}
              </div>

              {failing && (
                <dl className="mt-3 grid gap-x-4 gap-y-1 border-t border-deepRule pt-3 font-mono text-micro sm:grid-cols-[5rem_1fr]">
                  <dt className="text-white/40">Input</dt>
                  <dd className="whitespace-pre-wrap break-all text-white/80">{failing.input}</dd>
                  <dt className="text-white/40">Expected</dt>
                  <dd className="whitespace-pre-wrap break-all text-white/80">{failing.expected_output}</dd>
                  <dt className="text-white/40">Got</dt>
                  <dd className="whitespace-pre-wrap break-all text-hard">
                    {failing.actual_output || '(nothing)'}
                  </dd>
                </dl>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
