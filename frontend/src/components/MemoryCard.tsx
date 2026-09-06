import type { Genome } from '../types'

const ROWS: [string, (m: Genome) => string[]][] = [
  ['concepts', (m) => m.concepts],
  ['operations', (m) => m.operations],
  ['objective', (m) => (m.objective ? [m.objective] : [])],
  ['data structures', (m) => m.data_structures],
  ['approach', (m) => m.algorithm_hints],
  ['constraints', (m) => m.constraints],
]

/**
 * The extracted genome as a ledger: one labelled row per field, values as plain
 * mono terms.
 *
 * `ledgerOnly` exists so the recall flow can put the uncertainties in their own
 * panel *beside* this one. What you remembered and what you were unsure about
 * being physically separate on screen is the product's whole claim; keeping
 * them in one card made it a footnote.
 */
export default function MemoryCard({
  memory,
  ledgerOnly,
}: {
  memory: Genome
  ledgerOnly?: boolean
}) {
  const present = ROWS.map(([label, get]) => [label, get(memory)] as const)
    .filter(([, items]) => items?.length)
  const unsure = memory.uncertainties ?? []

  return (
    <div className="card">
      <dl className="divide-y divide-rule">
        {present.map(([label, items]) => (
          <div key={label} className="grid grid-cols-[7.5rem_1fr] gap-3 px-4 py-2.5">
            <dt className="label pt-0.5">{label}</dt>
            {/* Comma-separated rather than gap-spaced: "walk down  move
                diagonally" read as one four-word phrase, not two terms. */}
            <dd className="font-mono text-small">
              {items.map((item, i) => (
                <span key={item}>
                  {item}
                  {i < items.length - 1 && <span className="text-faint">,&nbsp;</span>}
                </span>
              ))}
            </dd>
          </div>
        ))}
        {present.length === 0 && (
          <div className="px-4 py-6 text-small text-muted">
            Nothing concrete came through. Try naming the shape of the data, or
            what you were asked to return.
          </div>
        )}
      </dl>

      {!ledgerOnly && unsure.length > 0 && (
        <div className="border-t border-ruleStrong bg-amberEarth/[0.07] px-4 py-3">
          <p className="label text-medium">not sure</p>
          <ul className="mt-1.5 space-y-1">
            {unsure.map((item) => (
              <li key={item} className="font-mono text-small text-shadowGrey">{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/**
 * The uncertainties, as their own panel.
 *
 * Renders even when empty — an absent panel would read as "we found nothing",
 * when the honest statement is "you sounded sure about all of it". Both are
 * information; only one of them is silence.
 */
export function UncertaintyPanel({ items }: { items: string[] }) {
  return (
    <div className="border border-amberEarth/40 bg-amberEarth/[0.07]">
      <p className="border-b border-amberEarth/30 px-4 py-2.5 font-mono text-micro text-medium">
        kept out of the search
      </p>
      {items.length > 0 ? (
        <>
          <ul className="divide-y divide-amberEarth/20">
            {items.map((item) => (
              <li key={item} className="px-4 py-2.5 font-mono text-small text-shadowGrey">
                {item}
              </li>
            ))}
          </ul>
          <p className="border-t border-amberEarth/30 px-4 py-2.5 text-tiny leading-relaxed text-muted">
            These never reach the query, so a detail you half-invented can't
            narrow the search against you.
          </p>
        </>
      ) : (
        <p className="px-4 py-2.5 text-tiny leading-relaxed text-muted">
          You didn't hedge on anything, so everything above is being searched on.
        </p>
      )}
    </div>
  )
}
