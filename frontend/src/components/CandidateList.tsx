import type { Candidate } from '../types'
import ConfidenceScore from './ConfidenceScore'

interface Props {
  candidates: Candidate[]
  onSelect: (candidate: Candidate) => void
}

/** Candidates are tabular data — title, match, difficulty, topics, who asks it —
 *  so they are rendered as a table rather than a stack of cards. Columns make
 *  the scores comparable down the page, which is the whole point of the screen. */
export default function CandidateList({ candidates, onSelect }: Props) {
  if (candidates.length === 0) {
    return (
      <p className="border border-rule bg-surface p-6 text-muted">
        No problem matched that memory closely enough. Add another detail — a
        constraint, an example, or what the answer looked like.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto border border-ruleStrong bg-surface">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-ruleStrong text-2xs text-muted">
            <th scope="col" className="px-4 py-2 font-medium">Problem</th>
            <th scope="col" className="px-4 py-2 font-medium">Match</th>
            <th scope="col" className="hidden px-4 py-2 font-medium sm:table-cell">Difficulty</th>
            <th scope="col" className="hidden px-4 py-2 font-medium md:table-cell">Topics</th>
            <th scope="col" className="hidden px-4 py-2 font-medium lg:table-cell">Asked at</th>
            <th scope="col" className="px-4 py-2"><span className="sr-only">Choose</span></th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr
              key={c.id}
              className="group border-b border-rule align-top last:border-0 hover:bg-floralWhite"
            >
              <td className="px-4 py-3">
                <div className="font-medium">{c.title}</div>
                {c.reason && (
                  <p className="mt-1 max-w-reading text-sm text-muted">{c.reason}</p>
                )}
              </td>
              <td className="px-4 py-3"><ConfidenceScore value={c.confidence} /></td>
              <td className="hidden px-4 py-3 sm:table-cell">
                {c.difficulty && (
                  <span className="font-mono text-sm text-muted">{c.difficulty}</span>
                )}
              </td>
              <td className="hidden px-4 py-3 md:table-cell">
                <ul className="space-y-0.5">
                  {(c.topics ?? []).slice(0, 3).map((t) => (
                    <li key={t} className="font-mono text-2xs text-muted">{t}</li>
                  ))}
                </ul>
              </td>
              <td className="hidden px-4 py-3 lg:table-cell">
                {c.company_count > 0 && (
                  <span className="text-sm text-muted">
                    {(c.companies ?? []).slice(0, 2).join(', ')}
                    {c.company_count > 2 && ` +${c.company_count - 2}`}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => onSelect(c)}
                  className="border border-prussianBlue px-3 py-1.5 text-sm font-medium
                             transition-colors hover:bg-prussianBlue hover:text-floralWhite
                             focus-visible:outline focus-visible:outline-2
                             focus-visible:outline-offset-2 focus-visible:outline-brownRed"
                >
                  Rebuild this
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
