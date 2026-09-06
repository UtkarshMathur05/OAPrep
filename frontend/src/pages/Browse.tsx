import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import type { FacetsResponse, ProblemSort, ProblemSummary } from '../types'
import { getFacets, listProblems } from '../services/api'
import ProblemTable from '../components/ProblemTable'

const PAGE = 25

const SORTS: { value: ProblemSort; label: string }[] = [
  { value: 'popularity', label: 'Most asked' },
  { value: 'companies', label: 'Most companies' },
  { value: 'difficulty', label: 'Easiest first' },
  { value: 'acceptance', label: 'Highest acceptance' },
  { value: 'title', label: 'A–Z' },
  { value: 'newest', label: 'Newest' },
]

/**
 * The corpus, filtered. Every filter lives in the URL, so a filtered view is a
 * link someone can send — which is most of what a problem directory is for.
 */
export default function Browse() {
  const [params, setParams] = useSearchParams()
  const [facets, setFacets] = useState<FacetsResponse | null>(null)
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [draftSearch, setDraftSearch] = useState(params.get('search') ?? '')

  const company = params.get('company') ?? ''
  const topic = params.get('topic') ?? ''
  const difficulty = params.get('difficulty') ?? ''
  const origin = params.get('origin') ?? ''
  const search = params.get('search') ?? ''
  const sort = (params.get('sort') as ProblemSort) ?? 'popularity'
  const offset = Number(params.get('offset') ?? 0)

  useEffect(() => {
    getFacets().then(setFacets).catch(() => setFacets(null))
  }, [])

  useEffect(() => {
    let live = true
    setLoading(true)
    setError(null)
    listProblems({
      limit: PAGE,
      offset,
      company: company || undefined,
      topic: topic || undefined,
      difficulty: difficulty || undefined,
      origin: (origin || undefined) as 'corpus' | 'community' | undefined,
      search: search || undefined,
      sort,
    })
      .then((res) => {
        if (!live) return
        setProblems(res.problems)
        setTotal(res.total)
      })
      .catch(() => live && setError('Could not load problems. Is the backend running?'))
      .finally(() => live && setLoading(false))
    return () => {
      live = false
    }
  }, [company, topic, difficulty, origin, search, sort, offset])

  /** Every filter change resets paging — page 4 of a different filter is a lie. */
  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('offset')
    setParams(next)
  }

  const active = useMemo(
    () =>
      [
        company && { key: 'company', label: company },
        topic && { key: 'topic', label: topic },
        difficulty && { key: 'difficulty', label: difficulty },
        origin && { key: 'origin', label: `${origin} problems` },
        search && { key: 'search', label: `“${search}”` },
      ].filter(Boolean) as { key: string; label: string }[],
    [company, topic, difficulty, origin, search],
  )

  return (
    <div className="shell grid gap-10 py-10 lg:grid-cols-[13.5rem_1fr]">
      <aside className="lg:sticky lg:top-16 lg:max-h-[calc(100vh-5rem)] lg:self-start lg:overflow-y-auto">
        <FacetGroup
          title="Difficulty"
          items={facets?.difficulties ?? []}
          selected={difficulty}
          capitalize
          onSelect={(v) => setFilter('difficulty', v)}
        />
        <FacetGroup
          title="Company"
          items={facets?.companies ?? []}
          selected={company}
          capitalize
          limit={12}
          onSelect={(v) => setFilter('company', v)}
          more={{ to: '/companies', label: 'All companies' }}
        />
        <FacetGroup
          title="Topic"
          items={facets?.topics ?? []}
          selected={topic}
          limit={12}
          onSelect={(v) => setFilter('topic', v)}
          more={{ to: '/topics', label: 'All topics' }}
        />
      </aside>

      <section className="min-w-0">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-h2">Problems</h1>
            <p className="mt-1.5 text-small text-muted">
              <span className="num font-mono">{total.toLocaleString()}</span>{' '}
              {total === 1 ? 'problem' : 'problems'}
              {active.length > 0 && ' matching your filters'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                setFilter('search', draftSearch.trim())
              }}
            >
              <input
                value={draftSearch}
                onChange={(e) => setDraftSearch(e.target.value)}
                placeholder="search titles and statements"
                className="field w-full font-mono text-micro sm:w-60"
              />
            </form>
            <label className="sr-only" htmlFor="sort">Sort</label>
            <select
              id="sort"
              value={sort}
              onChange={(e) => setFilter('sort', e.target.value)}
              className="field w-auto font-mono text-micro"
            >
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
        </div>

        {active.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {active.map((f) => (
              <button
                key={f.key}
                onClick={() => {
                  if (f.key === 'search') setDraftSearch('')
                  setFilter(f.key, '')
                }}
                className="inline-flex items-center gap-2 border border-ruleStrong bg-surface px-2 py-0.5
                           font-mono text-micro capitalize hover:border-brownRed hover:text-brownRed"
              >
                {f.label}
                <span aria-hidden className="text-faint">×</span>
                <span className="sr-only">Remove filter</span>
              </button>
            ))}
            <button
              onClick={() => { setDraftSearch(''); setParams(new URLSearchParams()) }}
              className="px-1 font-mono text-micro text-faint link hover:text-prussianBlue"
            >
              Clear all
            </button>
          </div>
        )}

        {error ? (
          <div role="alert" className="mt-5 border border-hard/30 border-l-2 border-l-hard bg-hard/5 px-4 py-3 text-small text-hard">
            {error}
          </div>
        ) : (
          <div className="mt-5">
            <ProblemTable problems={problems} loading={loading} />
          </div>
        )}

        {total > PAGE && (
          <div className="mt-4 flex items-center justify-between">
            <button
              className="btn-ghost"
              disabled={offset === 0}
              onClick={() => setFilter('offset', String(Math.max(0, offset - PAGE)))}
            >
              Previous
            </button>
            <span className="num font-mono text-micro text-faint">
              {offset + 1}–{Math.min(offset + PAGE, total)} of {total.toLocaleString()}
            </span>
            <button
              className="btn-ghost"
              disabled={offset + PAGE >= total}
              onClick={() => setFilter('offset', String(offset + PAGE))}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  )
}

function FacetGroup({
  title, items, selected, onSelect, limit, capitalize, more,
}: {
  title: string
  items: { name: string; count: number }[]
  selected: string
  onSelect: (value: string) => void
  limit?: number
  capitalize?: boolean
  more?: { to: string; label: string }
}) {
  const [expanded, setExpanded] = useState(false)
  const shown = limit && !expanded ? items.slice(0, limit) : items

  return (
    <div className="mb-7 border-t border-rule pt-4 first:border-t-0 first:pt-0">
      <h2 className="mb-2 font-mono text-micro text-faint">{title}</h2>
      <ul className="space-y-0.5">
        {shown.map((item) => {
          const isOn = selected === item.name
          return (
            <li key={item.name}>
              <button
                onClick={() => onSelect(isOn ? '' : item.name)}
                aria-pressed={isOn}
                className={`flex w-full items-baseline justify-between gap-2 px-2 py-1 text-left text-small transition-colors
                  ${isOn ? 'bg-prussianBlue text-white' : 'hover:bg-surface'}`}
              >
                <span className={`truncate ${capitalize ? 'capitalize' : ''}`}>{item.name}</span>
                <span className={`num font-mono text-micro ${isOn ? 'text-white/60' : 'text-faint'}`}>
                  {item.count}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      {limit && items.length > limit && (
        <button
          onClick={() => setExpanded((e) => !e)}
          className="mt-1 px-2 font-mono text-micro text-muted link hover:text-prussianBlue"
        >
          {expanded ? 'Show fewer' : `Show ${items.length - limit} more`}
        </button>
      )}
      {more && (
        <Link to={more.to} className="mt-1 block px-2 font-mono text-micro text-brownRed link">
          {more.label}
        </Link>
      )}
    </div>
  )
}
