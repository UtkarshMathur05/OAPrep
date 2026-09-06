import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { Facet, FacetsResponse, ProblemSummary } from '../types'
import { getFacets, listProblems } from '../services/api'
import { Difficulty, TopicsInline } from '../components/Tags'

const DIFFICULTIES = ['all', 'easy', 'medium', 'hard'] as const
type Diff = (typeof DIFFICULTIES)[number]

/**
 * The product home.
 *
 * This page used to be the recall box and nothing else, which sold one feature
 * and hid the thing most people actually arrive for: the questions a specific
 * company asks. So the order is now what someone showing up cold needs —
 * search, then the three ways in, then the companies themselves, then topics,
 * then the problems. Recall is presented as the strongest of the three ways in,
 * not as the site.
 */
export default function Home() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [facets, setFacets] = useState<FacetsResponse | null>(null)
  const [difficulty, setDifficulty] = useState<Diff>('all')
  const [problems, setProblems] = useState<ProblemSummary[]>([])

  useEffect(() => {
    getFacets().then(setFacets).catch(() => setFacets(null))
  }, [])

  useEffect(() => {
    listProblems({ limit: 8, difficulty: difficulty === 'all' ? undefined : difficulty })
      .then((r) => setProblems(r.problems))
      .catch(() => setProblems([]))
  }, [difficulty])

  const search = (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    navigate(q ? `/problems?search=${encodeURIComponent(q)}` : '/problems')
  }

  const t = facets?.totals

  return (
    <>
      {/* ------------------------------------------------------------ hero */}
      <section className="border-b border-line bg-panel">
        <div className="shell py-band-sm sm:py-14">
          <h1 className="max-w-[20ch] text-h1 sm:text-display">
            Practice the questions companies actually ask.
          </h1>
          <p className="mt-4 max-w-[62ch] text-lede text-ink2">
            An open, community-maintained bank of online-assessment and interview
            questions, tagged by the companies that set them. Search it, filter
            it, solve it in the browser — or describe a question you only half
            remember and let us find it.
          </p>

          <form onSubmit={search} className="mt-7 flex max-w-2xl gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="search a problem, a company, a topic…"
              aria-label="Search problems"
              className="field flex-1 py-2.5 text-base"
            />
            <button type="submit" className="btn-accent px-5">search</button>
          </form>

          <p className="mt-3 font-mono text-micro text-ink3">
            can't remember what it was called?{' '}
            <Link to="/recall" className="text-link link">describe it instead</Link>
          </p>

          <dl className="mt-8 flex flex-wrap gap-x-10 gap-y-4">
            {[
              ['problems', t?.problems],
              ['companies', t?.companies],
              ['topics', t?.topics],
              ['community-added', t?.community],
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
      </section>

      {/* --------------------------------------------------- ways in */}
      <section className="border-b border-line py-10">
        {/* The gap-px grid needs its own bounded box: painted onto `.shell` the
            gutter colour bled into the shell's horizontal padding and ran off
            both edges of the page. */}
        <div className="shell">
          <div className="grid gap-px border border-line bg-line sm:grid-cols-3">
          <Entry
            to="/companies"
            kicker="01"
            title="Browse by company"
            body="Every question we hold for a given company, ranked by how often it comes up."
          />
          <Entry
            to="/topics"
            kicker="02"
            title="Drill a topic"
            body="Arrays, dynamic programming, graphs — filtered down to the ones companies set."
          />
          <Entry
            to="/recall"
            kicker="03"
            title="Recall a problem"
            body="Describe what you remember and we reconstruct the problem from it."
            accent
            />
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------- companies */}
      <section className="band">
        <div className="shell">
          <SectionHead
            title="Companies"
            note="Counts come from 41,546 reported question–company pairs."
            to="/companies"
            cta={t ? `all ${t.companies.toLocaleString()} companies` : 'all companies'}
          />
          <div className="mt-6 grid gap-px border border-line bg-line sm:grid-cols-3 lg:grid-cols-6">
            {(facets?.companies.slice(0, 18) ?? Array.from({ length: 18 })).map((c, i) => {
              const f = c as Facet | undefined
              if (!f) return <div key={i} className="h-[4.5rem] animate-pulse bg-panel" />
              return (
                <Link
                  key={f.name}
                  to={`/problems?company=${encodeURIComponent(f.name)}`}
                  className="group bg-panel px-4 py-4 transition-colors hover:bg-raised"
                >
                  <p className="truncate capitalize group-hover:text-accent">{f.name}</p>
                  <p className="num mt-1 font-mono text-micro text-ink3">
                    {f.count.toLocaleString()} problems
                  </p>
                </Link>
              )
            })}
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------- topics */}
      <section className="band">
        <div className="shell">
          <SectionHead
            title="Topics"
            note="The tag on each question, and what recall matches a description against."
            to="/topics"
            cta={t ? `all ${t.topics.toLocaleString()} topics` : 'all topics'}
          />
          <div className="mt-6 flex flex-wrap gap-2">
            {(facets?.topics.slice(0, 20) ?? []).map((topic) => (
              <Link
                key={topic.name}
                to={`/problems?topic=${encodeURIComponent(topic.name)}`}
                className="flex items-baseline gap-2 border border-line bg-panel px-3 py-1.5
                           text-small transition-colors hover:border-lineStrong hover:text-accent"
              >
                {topic.name}
                <span className="num font-mono text-micro text-ink3">{topic.count}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------- questions */}
      <section className="band">
        <div className="shell">
          <SectionHead
            title="Most asked"
            note="Ordered by how many companies are reported to set them."
            to="/problems"
            cta="all problems"
          />

          <div className="mt-5 flex gap-1">
            {DIFFICULTIES.map((d) => (
              <button
                key={d}
                onClick={() => setDifficulty(d)}
                aria-pressed={difficulty === d}
                className={`border px-3 py-1 font-mono text-micro transition-colors ${
                  difficulty === d
                    ? 'border-lineStrong bg-raised text-ink'
                    : 'border-transparent text-ink3 hover:text-ink'
                }`}
              >
                {d}
              </button>
            ))}
          </div>

          <div className="mt-3 card overflow-x-auto">
            <table className="w-full min-w-[38rem] table-fixed border-collapse">
              <colgroup>
                <col className="w-[46%]" /><col className="w-[14%]" />
                <col className="w-[28%]" /><col className="w-[12%]" />
              </colgroup>
              <thead>
                <tr className="border-b border-line">
                  <th className="th">problem</th>
                  <th className="th">difficulty</th>
                  <th className="th">topics</th>
                  <th className="th text-right">companies</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {(problems.length ? problems : Array.from({ length: 8 })).map((row, i) => {
                  const p = row as ProblemSummary | undefined
                  if (!p) return <tr key={i}><td className="td h-[2.9rem]" colSpan={4} /></tr>
                  return (
                    <tr key={p.id} className="group hover:bg-raised">
                      <td className="td">
                        <Link to={`/problems/${p.slug}`} className="block truncate group-hover:underline">
                          {p.title}
                        </Link>
                      </td>
                      <td className="td"><Difficulty value={p.difficulty} /></td>
                      <td className="td"><TopicsInline names={p.topics} max={2} /></td>
                      <td className="num td text-right font-mono text-small text-ink2">
                        {p.company_count}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------- community */}
      <section className="py-band-sm sm:py-band">
        <div className="shell grid gap-8 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <h2 className="text-h2">Kept accurate by the people who sat the tests</h2>
            <p className="mt-3 max-w-reading text-ink2">
              Anyone can add a problem they were set. Every submission is first
              matched against what we already hold, so the bank corroborates
              rather than duplicates — and a community problem carries a
              visible confidence score that rises as more people independently
              describe the same thing.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/contribute" className="btn-accent">add a problem</Link>
              <Link to="/problems?origin=community" className="btn-ghost">
                see community problems
              </Link>
            </div>
          </div>

          {/* The confidence rule, stated rather than hidden in a tooltip — it is
              the mechanism the whole community model rests on. */}
          <div className="card p-5">
            <p className="label">how confidence works</p>
            <ol className="mt-3 space-y-2.5">
              {[
                ['one account', '35%', 'a single unverified recollection'],
                ['three accounts', '65%', 'independently described the same way'],
                ['five or more', '95%', 'the ceiling — never certain, but close'],
              ].map(([who, pct, why]) => (
                <li key={who} className="flex items-baseline gap-3">
                  <span className="num w-10 shrink-0 font-mono text-small text-medium">{pct}</span>
                  <span className="text-small">
                    {who}
                    <span className="block text-tiny text-ink3">{why}</span>
                  </span>
                </li>
              ))}
            </ol>
            <p className="mt-4 border-t border-line pt-3 text-tiny leading-relaxed text-ink3">
              Curated questions sit at 100% and do not move. Agreement with a
              question we already verified is logged, but it is not evidence.
            </p>
          </div>
        </div>
      </section>
    </>
  )
}

function Entry({
  to, kicker, title, body, accent,
}: { to: string; kicker: string; title: string; body: string; accent?: boolean }) {
  return (
    <Link to={to} className="group bg-panel px-5 py-6 transition-colors hover:bg-raised">
      <p className={`num font-mono text-micro ${accent ? 'text-accent' : 'text-ink3'}`}>{kicker}</p>
      <p className="mt-2 text-h3 group-hover:text-accent">{title}</p>
      <p className="mt-1.5 max-w-reading text-small text-ink2">{body}</p>
    </Link>
  )
}

function SectionHead({
  title, note, to, cta,
}: { title: string; note: string; to: string; cta: string }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 className="text-h2">{title}</h2>
        <p className="mt-1.5 max-w-reading text-small text-ink2">{note}</p>
      </div>
      <Link to={to} className="font-mono text-micro text-link link">{cta}</Link>
    </div>
  )
}
