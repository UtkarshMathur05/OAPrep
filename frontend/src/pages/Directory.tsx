import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Facet } from '../types'
import { getFacets } from '../services/api'

/**
 * The company and topic directories. One component, two routes — the pages
 * differ only in which facet list they read and how a name is written, and two
 * near-identical files would drift apart within a day.
 */
export default function Directory({ axis }: { axis: 'company' | 'topic' }) {
  const [items, setItems] = useState<Facet[] | null>(null)
  const [error, setError] = useState(false)
  const [q, setQ] = useState('')

  useEffect(() => {
    getFacets()
      .then((f) => setItems(axis === 'company' ? f.companies : f.topics))
      .catch(() => setError(true))
  }, [axis])

  const filtered = useMemo(
    () => (items ?? []).filter((i) => i.name.toLowerCase().includes(q.toLowerCase())),
    [items, q],
  )

  const copy =
    axis === 'company'
      ? {
          heading: 'Companies',
          blurb:
            'Reported from 41,546 company–question pairs. The count is how many ' +
            'problems in the corpus have been asked there.',
          label: 'Search companies',
        }
      : {
          heading: 'Topics',
          blurb:
            "LeetCode's own tags, carried through from each problem. They are also " +
            'what retrieval matches a memory against.',
          label: 'Search topics',
        }

  return (
    <div className="shell py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-reading">
          <h1 className="text-h2">{copy.heading}</h1>
          <p className="mt-1.5 text-small text-muted">{copy.blurb}</p>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={copy.label.toLowerCase()}
          className="field w-60 font-mono text-micro"
        />
      </div>

      {error && (
        <p role="alert" className="mt-6 border border-hard/30 border-l-2 border-l-hard bg-hard/5 px-4 py-3 text-small text-hard">
          Could not load the directory. Is the backend running?
        </p>
      )}

      <div className="mt-6 grid gap-px border border-ruleStrong bg-ruleStrong sm:grid-cols-2 lg:grid-cols-3">
        {(items === null ? Array.from({ length: 12 }) : filtered).map((item, i) => {
          const facet = item as Facet | undefined
          if (!facet) return <div key={i} className="h-[2.75rem] animate-pulse bg-surface" />
          return (
            <Link
              key={facet.name}
              to={`/problems?${axis}=${encodeURIComponent(facet.name)}`}
              className="group flex items-baseline justify-between gap-3 bg-surface px-4 py-3 transition-colors hover:bg-paper"
            >
              <span className={`truncate text-small ${axis === 'company' ? 'capitalize' : ''} group-hover:underline`}>
                {facet.name}
              </span>
              <span className="num shrink-0 font-mono text-micro text-faint">{facet.count}</span>
            </Link>
          )
        })}
      </div>

      {items !== null && filtered.length === 0 && (
        <p className="mt-6 text-small text-muted">Nothing matches “{q}”.</p>
      )}
    </div>
  )
}
