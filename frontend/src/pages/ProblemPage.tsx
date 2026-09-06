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
        <p role="alert" className="text-muted">{error}</p>
        <Link to="/problems" className="mt-3 inline-block text-small text-brownRed link">
          Back to all problems
        </Link>
      </div>
    )
  }

  if (!problem) {
    return (
      <div className="shell py-10">
        <div className="h-64 animate-pulse border border-rule bg-surface" />
      </div>
    )
  }

  return (
    <div className="shell grid gap-10 py-10 lg:grid-cols-[1fr_16rem]">
      <article className="min-w-0">
        <Link to="/problems" className="font-mono text-micro text-faint hover:text-prussianBlue">
          ← all problems
        </Link>

        <div className="mt-3 flex flex-wrap items-baseline gap-3">
          <h1 className="text-h1">{problem.title}</h1>
          <Difficulty value={problem.difficulty} />
          <Confidence problem={problem} />
        </div>

        {problem.origin === 'community' && (
          <p className="mt-5 border border-amberEarth/40 border-l-2 border-l-amberEarth bg-amberEarth/10 px-4 py-3 text-small text-shadowGrey">
            This problem was written from a user's description, not fetched from
            LeetCode. Parts of it are inferred. Its confidence rises each time
            somebody else independently describes the same problem.
          </p>
        )}

        <div className="mt-7 max-w-reading whitespace-pre-wrap leading-relaxed text-shadowGrey">
          {problem.description}
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-rule pt-6">
          <Link to={`/solve/${problem.slug}`} className="btn-primary">
            solve this problem
          </Link>
          {problem.source_url && (
            <a
              href={problem.source_url}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost"
            >
              open on LeetCode
            </a>
          )}
          <span className="font-mono text-micro text-faint">
            {problem.test_case_count > 0
              ? `${problem.test_case_count} stored test ${problem.test_case_count === 1 ? 'case' : 'cases'}`
              : 'Test cases are generated on your first run'}
          </span>
        </div>
      </article>

      <aside className="lg:sticky lg:top-16 lg:self-start">
        <dl className="divide-y divide-rule border border-rule bg-surface">
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
            <span className="font-mono text-small text-muted">{problem.recency ?? '—'}</span>
          </Row>
          <Row label="source">
            <span className="font-mono text-small capitalize text-muted">{problem.platform ?? '—'}</span>
          </Row>
        </dl>

        <div className="mt-4 border border-rule bg-surface px-4 py-3">
          <p className="text-small text-muted">
            Not quite the one you were thinking of?
          </p>
          <Link to="/recall" className="mt-1 inline-block text-small text-brownRed link">
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
