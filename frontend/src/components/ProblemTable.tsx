import { Link } from 'react-router-dom'
import type { ProblemSummary } from '../types'
import { Companies, Confidence, Difficulty, TopicsInline } from './Tags'

/**
 * The corpus as a table.
 *
 * A table, not a card grid: every column is something people scan down and
 * compare across rows — difficulty, how many companies ask it, acceptance.
 * Cards would break each of those comparisons into a separate glance.
 */
export default function ProblemTable({
  problems,
  loading,
  solved,
  attempted,
}: {
  problems: ProblemSummary[]
  loading?: boolean
  /** Slugs this session has completed, for the status column. */
  solved?: Set<string>
  /** Slugs it has run but not completed. */
  attempted?: Set<string>
}) {
  if (loading) {
    return (
      <div className="card divide-y divide-line">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="h-11 animate-pulse bg-ground" />
        ))}
      </div>
    )
  }

  if (!problems.length) {
    return (
      <div className="card px-5 py-12 text-center">
        <p className="text-small text-ink2">No problem matches those filters.</p>
        <p className="mt-2 text-small text-ink3">
          Clear a filter, or{' '}
          <Link to="/contribute" className="text-link link">
            add the one you are thinking of
          </Link>
          .
        </p>
      </div>
    )
  }

  return (
    <div className="card overflow-x-auto">
      {/* Widths live on the header cells rather than a <colgroup> because they
          have to change per breakpoint and a <col> cannot be hidden reliably.
          `table-fixed` still takes its grid from this first row, so the columns
          stay put as you page through — which was the point of the colgroup.

          Nothing is side-scrolled on a phone. A 7-column table forced a 52rem
          minimum, and that minimum escaped the scroll container: the whole page
          could be dragged 457px into empty space, which is the "page slides
          sideways" bug. Dropping to three columns on a small screen fixes that
          at the cause, and a table you scroll horizontally on a phone was not
          worth keeping anyway. */}
      <table className="w-full table-fixed border-collapse">
        <thead>
          <tr className="border-b border-line">
            <th className="th w-8"><span className="sr-only">Status</span></th>
            <th className="th w-[46%] sm:w-[38%] lg:w-[26%]">problem</th>
            <th className="th w-[26%] sm:w-[16%] lg:w-[13%]">difficulty</th>
            <th className="th hidden lg:table-cell lg:w-[19%]">topics</th>
            <th className="th hidden lg:table-cell lg:w-[20%]">asked at</th>
            <th className="th hidden text-right sm:table-cell sm:w-[16%] lg:w-[11%]">accepted</th>
            <th className="th w-[22%] text-right sm:w-[16%] lg:w-[9%]">
              <span className="sr-only">Solve</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {problems.map((p) => (
            <tr key={p.id} className="group hover:bg-raised">
              <td className="td text-center">
                <Status solved={solved?.has(p.slug)} attempted={attempted?.has(p.slug)} />
              </td>
              <td className="td">
                <Link
                  to={`/problems/${p.slug}`}
                  className="block truncate group-hover:underline"
                  title={p.title}
                >
                  {p.title}
                  <Confidence problem={p} />
                </Link>
              </td>
              <td className="td"><Difficulty value={p.difficulty} /></td>
              <td className="td hidden lg:table-cell"><TopicsInline names={p.topics} max={2} /></td>
              <td className="td hidden lg:table-cell">
                <Companies names={p.companies} total={p.company_count} />
              </td>
              <td className="num td hidden text-right font-mono text-small text-ink2 sm:table-cell">
                {p.acceptance != null ? `${p.acceptance.toFixed(0)}%` : '—'}
              </td>
              <td className="td text-right">
                {/* Dim rather than invisible. Hover-only revealed it to a mouse
                    and to nothing else — a touch screen has no hover, so on a
                    phone this column was permanently empty. */}
                <Link
                  to={`/solve/${p.slug}`}
                  className="tap justify-end font-mono text-micro text-ink3/60 transition-colors
                             group-hover:text-ink3 hover:!text-accent focus-visible:!text-accent"
                >
                  solve
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Solved / attempted, as a single glyph.
 *
 * A whole word per row would out-shout the titles, and this column is scanned
 * rather than read — you are looking for the gaps.
 */
function Status({ solved, attempted }: { solved?: boolean; attempted?: boolean }) {
  if (solved) {
    return <span className="text-easy" title="Solved" aria-label="Solved">✓</span>
  }
  if (attempted) {
    return <span className="text-medium" title="Attempted" aria-label="Attempted">·</span>
  }
  return <span className="sr-only">Not attempted</span>
}
