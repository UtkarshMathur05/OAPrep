// Shows the extracted Problem Genome.
// TODO(frontend): style the field groups.
import type { Genome } from '../types'

export default function MemoryCard({ memory }: { memory: Genome }) {
  return <pre className="rounded border p-3 text-sm">{JSON.stringify(memory, null, 2)}</pre>
}
