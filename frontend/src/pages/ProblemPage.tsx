import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { ProblemDetail } from '../types'
import { getProblem } from '../services/api'
import { Companies, Confidence, Difficulty, Topics } from '../components/Tags'

/** One corpus problem: the statement, its metadata, and the way into the IDE. */
export default function ProblemPage() {
  const { slug = '' } = useParams()
  const [problem, setProblem] = useState<ProblemDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setProblem(null)
    setError(null)
    getProblem(slug)
      .then(setProblem)
      .catch(() => setError('We could not find that problem.'))
  }, [slug])

  if (error) {
    return (
      <div className="shell max-w-reading py-20">
        <p role="alert" className="text-ink2">{error}</p>
        <Link to="/problems" className="tap mt-3 text-small text-link link">
          Back to all problems
        </Link>
      </div>
    )
  }

  if (!problem) {
    return (
      <div className="shell py-10">
        <div className="h-64 animate-pulse border border-line bg-panel" />
      </div>
    )
  }

  return (
    <div className="shell grid gap-10 py-10 lg:grid-cols-[1fr_16rem]">
      <article className="min-w-0">
        <Link to="/problems" className="tap font-mono text-micro text-ink3 hover:text-ink">
          ← all problems
        </Link>

        <div className="mt-3 flex flex-wrap items-baseline gap-3">
          <h1 className="text-h1">{problem.title}</h1>
          <Difficulty value={problem.difficulty} />
          <Confidence problem={problem} />
        </div>

        {problem.origin === 'community' && (
          <p className="mt-5 border border-medium/40 border-l-2 border-l-medium bg-medium/10 px-4 py-3 text-small text-ink2">
            This problem was written from a user's description, not fetched from
            a contributor's description rather than a verified source. Parts of
            it are inferred. Its confidence rises each time somebody else
            independently describes the same question.
          </p>
        )}

        {problem.io_format && (
          <section className="mt-7 max-w-reading border-l-2 border-accent bg-panel px-3 py-2">
            <h2 className="label">Input format</h2>
            <pre className="mt-1 whitespace-pre-wrap font-mono text-micro leading-relaxed text-ink">
              {problem.io_format}
            </pre>
          </section>
        )}

        <div className="mt-6 max-w-reading whitespace-pre-wrap leading-relaxed text-ink2">
          {problem.description}
        </div>

        <div className="mt-8 border-t border-line pt-6">
          {problem.solvable ? (
            <div className="flex flex-wrap items-center gap-3">
              <Link to={`/solve/${problem.slug}`} className="btn-accent">
                solve this problem
              </Link>
              {/* How many tests there are is not the reader's business before
                  they solve it — it is a hint about the shape of the answer,
                  and it goes stale the moment a run generates more. The one
                  thing worth saying is why a first run might be slow. */}
              {problem.test_case_count === 0 && (
                <span className="font-mono text-micro text-ink3">
                  Test cases are prepared on your first run
                </span>
              )}
            </div>
          ) : (
            /* No editor for a problem the judge can never return a verdict on.
               Opening one and failing at Run wastes the attempt and explains
               nothing. */
            <div className="max-w-reading">
              <p className="text-small leading-relaxed text-ink2">
                {problem.unsolvable_reason} You can still read it here — solve it
                where it can be checked.
              </p>
              {problem.source_url && (
                <a
                  href={problem.source_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="btn-accent mt-4 inline-block"
                >
                  solve on LeetCode
                </a>
              )}
            </div>
          )}
        </div>
      </article>

      <aside className="lg:sticky lg:top-16 lg:self-start">
        <dl className="divide-y divide-line border border-line bg-panel">
          <Row label="topics"><Topics names={problem.topics} max={8} /></Row>
          <Row label="asked at">
            <Companies names={problem.companies} total={problem.company_count} />
          </Row>
          <Row label="acceptance">
            <span className="num font-mono text-small">
              {problem.acceptance != null ? `${problem.acceptance.toFixed(1)}%` : '—'}
            </span>
          </Row>
          <Row label="last reported">
            <span className="font-mono text-small text-ink2">{problem.recency ?? '—'}</span>
          </Row>
          <Row label="source">
            <span className="font-mono text-small text-ink2">
              {problem.origin === 'community' ? 'community-contributed' : 'curated'}
            </span>
          </Row>
        </dl>

        <div className="mt-4 border border-line bg-panel px-4 py-3">
          <p className="text-small text-ink2">
            Not quite the one you were thinking of?
          </p>
          <Link to="/recall" className="tap mt-1 text-small text-link link">
            Describe what you remember instead
          </Link>
        </div>
      </aside>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="px-4 py-3">
      <dt className="label">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  )
}
