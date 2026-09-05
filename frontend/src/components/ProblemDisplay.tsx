import type { Problem, Provenance } from '../types'
import ConfidenceScore from './ConfidenceScore'

/** Each section is marked with where it came from. A margin key, not a badge
 *  on every heading: the reader should be able to scan the left edge and see
 *  at a glance which parts they actually remembered (CLAUDE.md §19). */
const MARK: Record<Provenance, { rail: string; dot: string; label: string }> = {
  remembered: {
    rail: 'border-l-2 border-brownRed',
    dot: 'bg-brownRed',
    label: 'You remembered this',
  },
  inferred: {
    rail: 'border-l-2 border-dashed border-amberEarth',
    dot: 'bg-amberEarth',
    label: 'Filled in by Memoize — you did not say this',
  },
  retrieved: {
    rail: 'border-l-2 border-rule',
    dot: 'bg-muted',
    label: 'From the original problem',
  },
}

function Section({
  title, field, problem, children,
}: {
  title: string
  field: string
  problem: Problem
  children: React.ReactNode
}) {
  const p = problem.provenance?.[field] as Provenance | undefined
  // No key means the pipeline made no claim — render it unmarked rather than
  // implying a provenance it never asserted.
  const mark = p ? MARK[p] : null

  return (
    <section className={`pl-4 ${mark ? mark.rail : 'border-l-2 border-transparent'}`}>
      <h3 className="mb-2 flex items-center gap-2 text-sm text-muted">
        {title}
        {mark && (
          <span className="inline-flex items-center gap-1.5" title={mark.label}>
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${mark.dot}`} />
            <span className="text-2xs">{p}</span>
          </span>
        )}
      </h3>
      {children}
    </section>
  )
}

export default function ProblemDisplay({ problem }: { problem: Problem }) {
  const legend: Provenance[] = ['remembered', 'retrieved', 'inferred']

  return (
    <article className="border border-ruleStrong bg-surface">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-ruleStrong px-6 py-4">
        <h2 className="text-2xl font-semibold tracking-tight">{problem.title}</h2>
        <ConfidenceScore value={problem.confidence} variant="figure" />
      </header>

      <div className="space-y-6 px-6 py-5">
        <Section title="Problem" field="description" problem={problem}>
          <p className="max-w-reading whitespace-pre-wrap leading-relaxed">
            {problem.description}
          </p>
        </Section>

        {problem.constraints?.length > 0 && (
          <Section title="Limits" field="constraints" problem={problem}>
            <ul className="space-y-1">
              {problem.constraints.map((c) => (
                <li key={c} className="font-mono text-sm">{c}</li>
              ))}
            </ul>
          </Section>
        )}

        {problem.examples?.length > 0 && (
          <Section title="Examples" field="examples" problem={problem}>
            <div className="space-y-3">
              {problem.examples.map((ex, i) => (
                <dl key={i} className="grid gap-1 border border-rule bg-floralWhite p-3
                                       font-mono text-sm sm:grid-cols-[4.5rem_1fr]">
                  <dt className="text-muted">Input</dt>
                  <dd className="whitespace-pre-wrap">{ex.input}</dd>
                  <dt className="text-muted">Output</dt>
                  <dd className="whitespace-pre-wrap text-brownRed">{ex.output}</dd>
                  {ex.explanation && (
                    <>
                      <dt className="text-muted">Why</dt>
                      <dd className="font-sans text-shadowGrey">{ex.explanation}</dd>
                    </>
                  )}
                </dl>
              ))}
            </div>
          </Section>
        )}

        {problem.notes?.length > 0 && (
          <section className="border-t border-rule pt-4">
            <h3 className="mb-2 text-sm text-muted">Worth knowing</h3>
            <ul className="max-w-reading space-y-1.5">
              {problem.notes.map((n) => (
                <li key={n} className="text-sm text-shadowGrey">{n}</li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <footer className="flex flex-wrap gap-4 border-t border-rule px-6 py-3">
        {legend.map((k) => (
          <span key={k} className="flex items-center gap-1.5 text-2xs text-muted">
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${MARK[k].dot}`} />
            {MARK[k].label}
          </span>
        ))}
      </footer>
    </article>
  )
}
