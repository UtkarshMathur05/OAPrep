// Ranked candidate problems; the user picks one to reconstruct.
import type { Candidate } from '../types'

interface Props {
  candidates: Candidate[]
  onSelect: (candidate: Candidate) => void
}

export default function CandidateList({ candidates, onSelect }: Props) {
  return (
    <ul className="space-y-2">
      {candidates.map((c) => (
        <li key={c.id}>
          <button className="w-full rounded border p-3 text-left" onClick={() => onSelect(c)}>
            {c.title} — {(c.confidence * 100).toFixed(0)}%
          </button>
        </li>
      ))}
    </ul>
  )
}
