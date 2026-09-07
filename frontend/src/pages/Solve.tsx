import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import type { Language, Problem, ProblemDetail, VerifyResponse } from '../types'
import { getLanguages, getProblem, getProblemProgress, verifySolution } from '../services/api'
import { MEMOIZE_DARK, defineTheme } from '../lib/monacoTheme'
import Timer from '../components/Timer'

const LANG_KEY = 'memoize.language'

/**
 * The solve environment.
 *
 * Full-bleed and dark, outside the site shell: once you are writing code the
 * navigation is a distraction. Statement left, editor right, results under the
 * editor — the layout every judge uses, because it is the one where you can
 * read a failing input without losing your place in the code.
 *
 * Run and Submit are different acts. Run is a trial and costs nothing; Submit
 * is the claim that you are finished, and only an accepted Submit completes the
 * problem. Submit therefore stays disabled until a Run has actually passed, and
 * goes back to disabled the moment the code changes — the evidence was about
 * the old code.
 */
export default function Solve() {
  const { slug = '' } = useParams()
  const location = useLocation()

  const handed = (location.state as { problem?: Problem } | null)?.problem ?? null

  const [problem, setProblem] = useState<ProblemDetail | Problem | null>(handed)
  const [allLanguages, setAllLanguages] = useState<Language[]>([])
  const [langId, setLangId] = useState<string>(
    () => localStorage.getItem(LANG_KEY) ?? 'python',
  )
  // One buffer per language, so switching to compare an approach and switching
  // back does not throw away what you wrote.
  const [buffers, setBuffers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<VerifyResponse | null>(null)
  const [running, setRunning] = useState<'run' | 'submit' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [solved, setSolved] = useState(false)
  const [runs, setRuns] = useState(0)
  const [proved, setProved] = useState(false)   // a Run passed for the code as it stands
  const [split, setSplit] = useState(42)

  const detail = problem && 'exec_mode' in problem ? problem : null
  const functional = detail?.exec_mode === 'functional'

  // Only what this problem can actually run. A functional problem needs both a
  // starter and a harness for the language; until the detail loads we show the
  // full list rather than an empty picker.
  const languages = useMemo(() => {
    const allowed = detail?.runnable_languages
    if (!allowed?.length) return allLanguages
    return allLanguages.filter((l) => allowed.includes(l.id))
  }, [allLanguages, detail])

  const language = useMemo(
    () => languages.find((l) => l.id === langId) ?? null,
    [languages, langId],
  )
  const code = buffers[langId] ?? ''

  useEffect(() => { getLanguages().then(setAllLanguages).catch(() => setAllLanguages([])) }, [])

  // Always fetch, even when the recall flow handed us a reconstructed problem.
  // A handed `Problem` carries the statement but none of `exec_mode`,
  // `code_snippets`, `runnable_languages` or `solvable` — so short-circuiting
  // the fetch gave every recalled problem the generic stdin starter, all eleven
  // languages, and no way to know it was a SQL question. The handed copy is the
  // placeholder that renders while this lands, nothing more.
  useEffect(() => {
    if (!slug) return
    getProblem(slug)
      .then(setProblem)
      .catch(() => { if (!handed) setError('We could not load that problem.') })
  }, [slug, handed])

  // Progress survives a reload: the counter is the database's, not the tab's.
  useEffect(() => {
    if (!slug) return
    getProblemProgress(slug)
      .then((p) => { setSolved(p.solved); setRuns(p.runs) })
      .catch(() => undefined)
  }, [slug])

  // The remembered language may not be one this problem supports. Move to one
  // it does instead of leaving the editor on a language that cannot run.
  useEffect(() => {
    if (!languages.length || languages.some((l) => l.id === langId)) return
    setLangId(languages[0].id)
  }, [languages, langId])

  // Seed a buffer the first time a language is shown.
  //
  // Three sources, most specific first: the problem's own starter for this
  // language (functional problems carry one per language, written for their
  // signature), then a reconstruction's Python starter, then the generic
  // stdin template.
  useEffect(() => {
    // Wait for the problem, not just the language list. /languages usually wins
    // the race, and seeding from it first would lock in the generic stdin
    // template for a functional problem — whose own starter then never applies,
    // because a seeded buffer is never re-seeded.
    // `detail`, not `problem`: a handed reconstruction is truthy immediately and
    // would seed the stdin template before the real starter arrives.
    if (!language || !detail || buffers[language.id] !== undefined) return
    const seed = detail?.code_snippets?.[language.id]
      ?? (language.id === 'python' && handed?.starter_code
        ? handed.starter_code
        : language.starter)
    setBuffers((b) => ({ ...b, [language.id]: seed }))
  }, [language, buffers, handed, detail, problem])

  const problemId = (problem as ProblemDetail | null)?.id ?? handed?.id ?? null

  const send = useCallback(async (kind: 'run' | 'submit') => {
    if (!problemId || !code.trim()) return
    setRunning(kind)
    setError(null)
    setResult(null)
    try {
      const res = await verifySolution({ problem_id: problemId, code, language: langId, kind })
      setResult(res)
      setSolved(res.solved)
      setRuns(res.runs)
      if (kind === 'run') setProved(res.all_passed)
    } catch {
      setError('The run did not come back. The judge may be rate-limited — try again in a moment.')
    } finally {
      setRunning(null)
    }
  }, [problemId, code, langId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        send(e.shiftKey && proved ? 'submit' : 'run')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [send, proved])

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

  const changeLanguage = (id: string) => {
    setLangId(id)
    localStorage.setItem(LANG_KEY, id)
    setResult(null)
    setProved(false)   // the passing run was about the other language
  }

  const editCode = (next: string) => {
    setBuffers((b) => ({ ...b, [langId]: next }))
    // The proof was about the code that ran, not the code on screen.
    if (proved) setProved(false)
  }

  // Reachable by typing the URL, and by any stale link. An editor that cannot
  // return a verdict is worse than no editor, so say why and send them on.
  if (detail && !detail.solvable) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-5 bg-ground px-6 text-center text-ink">
        <h1 className="text-h3">{detail.title}</h1>
        <p className="max-w-reading text-small leading-relaxed text-ink2">
          {detail.unsolvable_reason}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {detail.source_url && (
            <a
              href={detail.source_url}
              target="_blank"
              rel="noreferrer noopener"
              className="btn-accent"
            >
              solve on LeetCode
            </a>
          )}
          <Link to={`/problems/${detail.slug}`} className="btn-ghost">
            back to the problem
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col bg-ground text-ink">
      <header className="flex shrink-0 items-center gap-4 border-b border-line px-4 py-2.5">
        <Link
          to={problem && 'slug' in problem ? `/problems/${problem.slug}` : '/problems'}
          className="font-mono text-micro text-ink3 transition-colors hover:text-ink"
        >
          ← back
        </Link>
        <span className="truncate font-medium">{problem?.title ?? 'Loading…'}</span>
        {solved && (
          <span className="shrink-0 border border-easy/40 bg-easy/10 px-2 py-0.5 font-mono text-micro text-easy">
            solved
          </span>
        )}

        <div className="ml-auto flex items-center gap-4">
          <span className="num hidden font-mono text-micro text-ink3 sm:inline">
            {runs} {runs === 1 ? 'run' : 'runs'}
          </span>
          <Timer />

          <label htmlFor="lang" className="sr-only">Language</label>
          <select
            id="lang"
            value={langId}
            onChange={(e) => changeLanguage(e.target.value)}
            className="field w-auto py-1 font-mono text-micro"
          >
            {languages.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
          </select>

          <button
            onClick={() => send('run')}
            disabled={!!running || !problemId}
            className="btn-ghost"
          >
            {running === 'run' ? 'running…' : 'run tests'}
          </button>
          <button
            onClick={() => send('submit')}
            disabled={!!running || !problemId || !proved}
            title={proved ? undefined : 'Run the tests first — submitting needs a passing run'}
            className="btn-accent"
          >
            {running === 'submit' ? 'submitting…' : 'submit'}
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <section
          style={{ width: `${split}%` }}
          className="min-w-0 overflow-y-auto border-r border-line px-6 py-5"
        >
          {error && !problem && <p role="alert" className="text-hard">{error}</p>}
          {problem && (
            <>
              <h1 className="text-h3">{problem.title}</h1>

              {/* Above the statement, deliberately. Curated statements are
                  written for a function signature and show arguments as array
                  literals (`triangle = [[2],[3,4]]`), which is not what your
                  program reads. Whoever sees that first will write the wrong
                  parser, so the real contract goes first. */}
              {problem.io_format && (
                <section className="mt-4 border-l-2 border-accent bg-panel px-3 py-2">
                  <h2 className="label">Input format</h2>
                  <pre className="mt-1 whitespace-pre-wrap font-mono text-micro leading-relaxed text-ink">
                    {problem.io_format}
                  </pre>
                  {'origin' in problem && problem.origin === 'corpus' && (
                    <p className="mt-2 text-micro leading-relaxed text-ink3">
                      The examples in the statement below are written as array
                      literals. That is not what your program reads — read stdin
                      exactly as described here.
                    </p>
                  )}
                </section>
              )}

              <div className="mt-5 max-w-reading whitespace-pre-wrap text-small leading-relaxed text-ink2">
                {problem.description}
              </div>

              {'constraints' in problem && problem.constraints?.length > 0 && (
                <>
                  <h2 className="mt-6 text-small font-medium">Constraints</h2>
                  <ul className="mt-2 space-y-1 font-mono text-micro text-ink2">
                    {problem.constraints.map((c) => <li key={c}>{c}</li>)}
                  </ul>
                </>
              )}

              {'examples' in problem && problem.examples?.length > 0 && (
                <>
                  <h2 className="mt-6 text-small font-medium">Examples</h2>
                  <div className="mt-2 space-y-3">
                    {problem.examples.map((ex, i) => (
                      <div key={i} className="border border-line bg-panel p-3 font-mono text-micro">
                        <p className="text-ink3">Input</p>
                        <pre className="mt-1 whitespace-pre-wrap text-ink">{ex.input}</pre>
                        <p className="mt-2 text-ink3">Output</p>
                        <pre className="mt-1 whitespace-pre-wrap text-ink">{ex.output}</pre>
                        {ex.explanation && <p className="mt-2 text-ink3">{ex.explanation}</p>}
                      </div>
                    ))}
                  </div>
                </>
              )}

              <p className="mt-8 border-t border-line pt-4 font-mono text-micro leading-relaxed text-ink3">
                {functional ? (
                  <>
                    Fill in the method above and return the answer. Arguments
                    arrive exactly as the examples show them, so there is
                    nothing to parse.
                  </>
                ) : (
                  <>
                    Your program reads all of stdin and prints the answer to
                    stdout.
                    {problem.io_format
                      ? ' Read it exactly as the input format describes.'
                      : ' Test inputs are given exactly as shown above.'}{' '}
                    The same cases run against every language.
                  </>
                )}
              </p>
            </>
          )}
        </section>

        <div
          role="separator"
          aria-orientation="vertical"
          onMouseDown={() => { dragging.current = true; document.body.style.cursor = 'col-resize' }}
          className="w-1 shrink-0 cursor-col-resize bg-line transition-colors hover:bg-accent"
        />

        <section className="flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-1">
            <Editor
              height="100%"
              language={language?.monaco ?? 'python'}
              path={`solution.${langId}`}
              value={code}
              theme={MEMOIZE_DARK}
              beforeMount={defineTheme}
              onChange={(v) => editCode(v ?? '')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
                padding: { top: 16, bottom: 16 },
                scrollBeyondLastLine: false,
                smoothScrolling: true,
                renderLineHighlight: 'gutter',
                overviewRulerBorder: false,
              }}
            />
          </div>
          <Console result={result} running={running} error={error} proved={proved} solved={solved} />
        </section>
      </div>
    </div>
  )
}

function Console({
  result, running, error, proved, solved,
}: {
  result: VerifyResponse | null
  running: 'run' | 'submit' | null
  error: string | null
  proved: boolean
  solved: boolean
}) {
  const [open, setOpen] = useState(true)
  const passed = result ? result.all_passed : false
  const failing = result?.results?.find((r) => !r.passed)

  return (
    <div className="shrink-0 border-t border-line bg-panel">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-4 py-2 text-left">
        <span className="font-mono text-small">results</span>
        {running && <span className="font-mono text-micro text-accent">{running}ning…</span>}
        {result && (
          <>
            <span className={`font-mono text-small ${passed ? 'text-easy' : 'text-hard'}`}>
              {result.status}
            </span>
            <span className="num font-mono text-micro text-ink3">
              {result.passed}/{result.total} passed
              {result.runtime && ` · ${result.runtime}`}
              {result.memory && ` · ${result.memory}`}
            </span>
          </>
        )}
        <span className="ml-auto font-mono text-micro text-ink3">{open ? 'hide' : 'show'}</span>
      </button>

      {open && (
        <div className="max-h-56 overflow-y-auto border-t border-line px-4 py-3">
          {error && <p role="alert" className="text-small text-hard">{error}</p>}

          {!result && !running && !error && (
            <p className="text-small text-ink3">
              Run your solution against the stored test cases.
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
                      ${r.passed ? 'bg-easy/15 text-easy' : 'bg-hard/15 text-hard'}`}
                  >
                    {r.index + 1}
                  </span>
                ))}
              </div>

              {/* The one line that tells you what to do next. */}
              {result.kind === 'submit' && result.all_passed ? (
                <p className="mt-3 border-t border-line pt-3 font-mono text-micro text-easy">
                  accepted — marked complete after {result.runs}{' '}
                  {result.runs === 1 ? 'run' : 'runs'} and {result.submissions}{' '}
                  {result.submissions === 1 ? 'submission' : 'submissions'}
                </p>
              ) : proved && !solved ? (
                <p className="mt-3 border-t border-line pt-3 font-mono text-micro text-accent">
                  all tests pass — submit to mark this complete
                </p>
              ) : null}

              {failing && (
                <dl className="mt-3 grid gap-x-4 gap-y-1 border-t border-line pt-3 font-mono text-micro sm:grid-cols-[5rem_1fr]">
                  <dt className="text-ink3">input</dt>
                  <dd className="whitespace-pre-wrap break-all text-ink">{failing.input}</dd>
                  <dt className="text-ink3">expected</dt>
                  <dd className="whitespace-pre-wrap break-all text-ink">{failing.expected_output}</dd>
                  <dt className="text-ink3">got</dt>
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
