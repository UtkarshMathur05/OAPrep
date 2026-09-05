// Renders the reconstructed problem statement.
// TODO(frontend): render description as markdown.
import type { Problem } from '../types'

export default function ProblemDisplay({ problem }: { problem: Problem }) {
  return (
    <article className="space-y-3">
      <h2 className="text-xl font-semibold">{problem.title}</h2>
      <p>{problem.description}</p>
      <ul className="list-disc pl-5 text-sm">
        {problem.constraints.map((c) => <li key={c}>{c}</li>)}
      </ul>
    </article>
  )
}
