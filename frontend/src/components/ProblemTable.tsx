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
}: {
  problems: ProblemSummary[]
  loading?: boolean
}) {
  if (loading) {
    return (
      <div className="card divide-y divide-rule">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="h-11 animate-pulse bg-paper" />
        ))}
      </div>
    )
  }

  if (!problems.length) {
    return (
      <div className="card px-5 py-12 text-center">
        <p className="text-small text-muted">No problem matches those filters.</p>
        <p className="mt-2 text-small text-faint">
          Clear a filter, or{' '}
          <Link to="/contribute" className="text-brownRed link">
            add the one you are thinking of
          </Link>
          .
        </p>
      </div>
    )
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[52rem] table-fixed border-collapse">
        {/* Fixed widths: without them the columns resize as you page through,
            and a table whose grid moves is harder to read than a list. */}
        <colgroup>
          <col className="w-[31%]" />
          <col className="w-[10%]" />
          <col className="w-[25%]" />
          <col className="w-[20%]" />
          <col className="w-[8%]" />
          <col className="w-[6%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-rule">
            <th className="th">problem</th>
            <th className="th">difficulty</th>
            <th className="th">topics</th>
            <th className="th">asked at</th>
            <th className="th text-right">accepted</th>
            <th className="th" />
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {problems.map((p) => (
            <tr key={p.id} className="group hover:bg-paper">
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
              <td className="td"><TopicsInline names={p.topics} max={2} /></td>
              <td className="td"><Companies names={p.companies} total={p.company_count} /></td>
              <td className="num td text-right font-mono text-small text-muted">
                {p.acceptance != null ? `${p.acceptance.toFixed(0)}%` : '—'}
              </td>
              <td className="td text-right">
                <Link
                  to={`/solve/${p.slug}`}
                  className="font-mono text-micro text-faint opacity-0 transition-opacity
                             group-hover:opacity-100 focus:opacity-100 hover:text-brownRed"
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
