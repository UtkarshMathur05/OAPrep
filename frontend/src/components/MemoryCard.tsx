import type { Genome } from '../types'

/** The extracted genome as a ledger: one labelled row per field, values as
 *  plain terms. What you said and what you were unsure about are separated
 *  structurally, not just tinted — that split is the product's whole claim. */
export default function MemoryCard({ memory }: { memory: Genome }) {
  const rows: [string, string[]][] = [
    ['Topic', memory.concepts],
    ['What you do', memory.operations],
    ['Goal', memory.objective ? [memory.objective] : []],
    ['Data', memory.data_structures],
    ['Approach', memory.algorithm_hints],
    ['Limits', memory.constraints],
  ]
  const present = rows.filter(([, items]) => items?.length)
  const unsure = memory.uncertainties ?? []

  return (
    <div className="border border-ruleStrong bg-surface">
      <dl className="divide-y divide-rule">
        {present.map(([label, items]) => (
          <div key={label} className="grid grid-cols-[7rem_1fr] gap-4 px-4 py-3">
            <dt className="pt-0.5 text-sm text-muted">{label}</dt>
            <dd className="flex flex-wrap gap-x-4 gap-y-1">
              {items.map((item) => (
                <span key={item} className="font-mono text-sm">{item}</span>
              ))}
            </dd>
          </div>
        ))}
        {present.length === 0 && (
          <div className="px-4 py-6 text-muted">
            Nothing concrete came through. Try naming the shape of the data, or
            what you were asked to return.
          </div>
        )}
      </dl>

      {unsure.length > 0 && (
        <div className="border-t border-ruleStrong bg-amberEarth/[0.07] px-4 py-3">
          <div className="grid grid-cols-[7rem_1fr] gap-4">
            <span className="pt-0.5 text-sm text-amberEarth">Not sure</span>
            <ul className="space-y-1">
              {unsure.map((item) => (
                <li key={item} className="font-mono text-sm text-shadowGrey">{item}</li>
              ))}
            </ul>
          </div>
          <p className="mt-2 pl-[7.75rem] text-sm text-muted">
            These are kept out of the search so a wrong guess can't narrow it for you.
          </p>
        </div>
      )}
    </div>
  )
}
