import type { Candidate } from '../types'
import ConfidenceScore from './ConfidenceScore'
import { Companies, Difficulty, TopicsInline } from './Tags'

interface Props {
  candidates: Candidate[]
  onSelect: (candidate: Candidate) => void
}

/**
 * Candidates are tabular data — title, match, difficulty, topics, who asks it —
 * so they are a table rather than a stack of cards. Columns make the scores
 * comparable down the page, which is the whole point of the screen.
 *
 * The top row's action is the primary button. Reranking has already done the
 * work of deciding; making every row's button identical threw that away and
 * asked the user to redo it.
 */
export default function CandidateList({ candidates, onSelect }: Props) {
  if (candidates.length === 0) {
    return (
      <p className="card p-6 text-small text-muted">
        No problem matched that memory closely enough. Add another detail — a
        constraint, an example, or what the answer looked like.
      </p>
    )
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[46rem] table-fixed border-collapse text-left">
        <colgroup>
          <col className="w-[36%]" />
          <col className="w-[12%]" />
          <col className="w-[10%]" />
          <col className="w-[23%]" />
          <col className="w-[19%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-rule">
            <th scope="col" className="th">problem</th>
            <th scope="col" className="th">match</th>
            <th scope="col" className="th hidden sm:table-cell">difficulty</th>
            <th scope="col" className="th hidden md:table-cell">topics</th>
            <th scope="col" className="th text-right">asked at</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {candidates.map((c, i) => (
            <tr key={c.id} className={i === 0 ? 'bg-floralWhite/60' : undefined}>
              <td className="td">
                <div className="font-medium">{c.title}</div>
                {c.reason && (
                  <p className="mt-1 text-tiny leading-relaxed text-muted">{c.reason}</p>
                )}
                <button
                  onClick={() => onSelect(c)}
                  className={`mt-2.5 ${i === 0 ? 'btn-accent btn-sm' : 'btn-ghost btn-sm'}`}
                >
                  {i === 0 ? 'rebuild this' : 'rebuild'}
                </button>
              </td>
              <td className="td align-top"><ConfidenceScore value={c.confidence} /></td>
              <td className="td hidden align-top sm:table-cell">
                <Difficulty value={c.difficulty} />
              </td>
              <td className="td hidden align-top md:table-cell">
                <TopicsInline names={c.topics ?? []} max={2} />
              </td>
              <td className="td align-top text-right">
                <Companies names={c.companies ?? []} total={c.company_count} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
