import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { FacetsResponse, ProblemSummary } from '../types'
import { getFacets, listProblems } from '../services/api'
import { Difficulty, TopicsInline } from '../components/Tags'

/** Memories that actually resolve, so the example is a demo and not a slogan. */
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

const PIPELINE = [
  ['memory', 'however vague, spoken or typed'],
  ['genome', 'concepts and objective, uncertainty kept separate'],
  ['retrieval', 'vector search across every statement, then a rerank'],
  ['reconstruction', 'each part labelled remembered, retrieved or inferred'],
  ['verification', 'your Python, real test cases, real execution'],
]

/**
 * The landing page is the recall box.
 *
 * A problem list is table stakes — every OA site has one, and ours is one click
 * away in the nav. So the hero is not a pitch with an input somewhere below it;
 * the input *is* the hero, at full width, with nothing beside it competing for
 * the same glance. Everything under it is quiet by comparison.
 */
export default function Landing() {
  const navigate = useNavigate()
  const [transcript, setTranscript] = useState('')
  const [facets, setFacets] = useState<FacetsResponse | null>(null)
  const [top, setTop] = useState<ProblemSummary[]>([])

  useEffect(() => {
    getFacets().then(setFacets).catch(() => setFacets(null))
    listProblems({ limit: 8 }).then((r) => setTop(r.problems)).catch(() => setTop([]))
  }, [])

  const start = (text: string) => {
    const t = text.trim()
    if (t) navigate('/recall', { state: { transcript: t } })
  }

  return (
    <>
      {/* ---------------------------------------------------------- hero */}
      <section className="border-b border-rule bg-floralWhite py-band-sm sm:py-20">
        <div className="shell">
          <h1 className="max-w-[24ch] text-h1 sm:text-display">
            Recall the coding problem you can't quite name.
          </h1>
          <p className="mt-5 max-w-[58ch] text-lede text-shadowGrey">
            Describe whatever stuck — the shape of the input, what you had to
            return, a constraint you half remember. We rebuild the problem, and
            keep what you actually remembered separate from what we inferred.
          </p>

          <div className="mt-8 max-w-[52rem] border border-prussianBlue bg-surface">
            <label htmlFor="recall" className="sr-only">
              What do you remember about the problem?
            </label>
            <div className="flex gap-3 px-4 pt-4">
              <span aria-hidden className="select-none font-mono text-base text-brownRed">
                &gt;
              </span>
              <textarea
                id="recall"
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) start(transcript)
                }}
                rows={3}
                placeholder="a grid where you could only move right or down, and you had to minimise the total…"
                className="w-full resize-none bg-transparent text-base leading-relaxed
                           placeholder:text-faint focus:outline-none"
              />
            </div>
            <div className="mt-2 flex items-center justify-between border-t border-rule px-3 py-2">
              <span className="font-mono text-micro text-faint">⌘↵ to search 1,124 problems</span>
              <button
                onClick={() => start(transcript)}
                disabled={!transcript.trim()}
                className="btn-accent"
              >
                recall it
              </button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-baseline gap-2">
            <span className="label">or try</span>
            {EXAMPLES.map((ex) => (
              <button key={ex.chip} onClick={() => setTranscript(ex.text)} className="chip">
                {ex.chip}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------ pipeline */}
      {/* Genuinely a sequence, which is the only thing that earns numbering. */}
      <section className="border-b border-rule bg-surface">
        <div className="shell">
          <ol className="grid divide-y divide-rule sm:grid-cols-5 sm:divide-x sm:divide-y-0">
            {PIPELINE.map(([name, detail], i) => (
              <li key={name} className="py-5 sm:px-4 sm:first:pl-0 sm:last:pr-0">
                <p className="font-mono text-micro text-faint">
                  {String(i + 1).padStart(2, '0')}
                </p>
                <p className="mt-1.5 font-mono text-small font-medium">{name}</p>
                <p className="mt-1 text-tiny leading-relaxed text-muted">{detail}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* -------------------------------------------------------- corpus */}
      <section className="band">
        <div className="shell">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-h2">The corpus underneath</h2>
              <p className="mt-1.5 max-w-reading text-small text-muted">
                Real LeetCode statements, tagged with the companies that ask them
                across 41,546 reported question–company pairs. Recall searches
                this; so can you.
              </p>
            </div>
            <dl className="flex gap-6">
              {[
                ['problems', facets?.totals.problems],
                ['companies', facets?.totals.companies],
                ['topics', facets?.totals.topics],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <dd className="num font-mono text-h3">
                    {value == null ? '—' : (value as number).toLocaleString()}
                  </dd>
                  <dt className="label">{label as string}</dt>
                </div>
              ))}
            </dl>
          </div>

          <div className="mt-6 card overflow-x-auto">
            <table className="w-full min-w-[38rem] table-fixed border-collapse">
              <colgroup>
                <col className="w-[46%]" />
                <col className="w-[14%]" />
                <col className="w-[28%]" />
                <col className="w-[12%]" />
              </colgroup>
              <thead>
                <tr className="border-b border-rule">
                  <th className="th">most asked</th>
                  <th className="th">difficulty</th>
                  <th className="th">topics</th>
                  <th className="th text-right">companies</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {(top.length ? top : Array.from({ length: 8 })).map((row, i) => {
                  const p = row as ProblemSummary | undefined
                  if (!p) return <tr key={i}><td className="td h-[2.9rem]" colSpan={4} /></tr>
                  return (
                    <tr key={p.id} className="group hover:bg-paper">
                      <td className="td">
                        <Link to={`/problems/${p.slug}`} className="block truncate group-hover:underline">
                          {p.title}
                        </Link>
                      </td>
                      <td className="td"><Difficulty value={p.difficulty} /></td>
                      <td className="td"><TopicsInline names={p.topics} max={2} /></td>
                      <td className="num td text-right font-mono text-small text-muted">
                        {p.company_count}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4">
            <Link to="/problems" className="btn-ghost">browse all 1,124</Link>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------- rails */}
      <section className="band">
        <div className="shell grid gap-10 lg:grid-cols-2">
          <Rail
            title="By company"
            note="Count is how many corpus problems that company has been reported to ask."
            items={facets?.companies.slice(0, 15) ?? []}
            href={(n) => `/problems?company=${encodeURIComponent(n)}`}
            all={{ to: '/companies', label: 'all 608 companies' }}
            capitalize
          />
          <Rail
            title="By topic"
            note="LeetCode's own tags. They are also what retrieval matches a memory against."
            items={facets?.topics.slice(0, 15) ?? []}
            href={(n) => `/problems?topic=${encodeURIComponent(n)}`}
            all={{ to: '/topics', label: 'all 143 topics' }}
          />
        </div>
      </section>

      {/* ---------------------------------------------------- contribute */}
      <section className="py-band-sm sm:py-band">
        <div className="shell flex flex-wrap items-center justify-between gap-6">
          <div className="max-w-reading">
            <h2 className="text-h3">We don't have it? Describe it anyway.</h2>
            <p className="mt-1.5 text-small text-muted">
              Contributing runs the same search first. If we already have the
              problem you get told so and your account raises its confidence; if
              we don't, we write it up, generate test cases, and store it as a
              community problem starting at 35%.
            </p>
          </div>
          <Link to="/contribute" className="btn-ghost">contribute a problem</Link>
        </div>
      </section>
    </>
  )
}

function Rail({
  title, note, items, href, all, capitalize,
}: {
  title: string
  note: string
  items: { name: string; count: number }[]
  href: (name: string) => string
  all: { to: string; label: string }
  capitalize?: boolean
}) {
  return (
    <div>
      <h2 className="text-h3">{title}</h2>
      <p className="mt-1.5 max-w-reading text-small text-muted">{note}</p>
      <ul className="mt-4 border-t border-rule">
        {(items.length ? items : Array.from({ length: 8 })).map((item, i) => {
          const f = item as { name: string; count: number } | undefined
          if (!f) return <li key={i} className="h-8 border-b border-rule" />
          return (
            <li key={f.name} className="border-b border-rule">
              <Link
                to={href(f.name)}
                className="flex items-baseline justify-between gap-3 py-1.5 transition-colors hover:text-brownRed"
              >
                <span className={`text-small ${capitalize ? 'capitalize' : ''}`}>{f.name}</span>
                <span className="num font-mono text-micro text-faint">{f.count}</span>
              </Link>
            </li>
          )
        })}
      </ul>
      <Link to={all.to} className="mt-3 inline-block font-mono text-micro text-brownRed link">
        {all.label}
      </Link>
    </div>
  )
}
