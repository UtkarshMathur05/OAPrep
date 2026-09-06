import { Link } from 'react-router-dom'
import type { ProblemSummary } from '../types'

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: 'text-easy',
  medium: 'text-medium',
  hard: 'text-hard',
}

/** Difficulty as coloured text, not a filled pill. In a table of 50 rows,
 *  50 pills is noise; the word alone carries it. */
export function Difficulty({ value }: { value?: string | null }) {
  if (!value) return <span className="text-faint">—</span>
  return (
    <span className={`font-mono text-small ${DIFFICULTY_COLOR[value] ?? 'text-muted'}`}>
      {value[0].toUpperCase() + value.slice(1)}
    </span>
  )
}

/**
 * "Google, Amazon +124" — the count is the interesting part.
 *
 * Held to a single line on purpose. Wrapping this cell made every table row a
 * different height, which destroys the one thing a table is for: scanning a
 * column without your eye having to re-find the baseline.
 */
export function Companies({ names, total, max = 2 }: { names: string[]; total: number; max?: number }) {
  if (!names.length) return <span className="text-faint">—</span>
  const shown = names.slice(0, max).map(title).join(', ')
  const rest = total - Math.min(names.length, max)
  return (
    <span className="block truncate text-small text-muted">
      {shown}
      {rest > 0 && <span className="text-faint"> +{rest}</span>}
    </span>
  )
}

export function Topics({ names, max = 3 }: { names: string[]; max?: number }) {
  if (!names.length) return null
  return (
    // flex-nowrap: same reason as Companies — a wrapping tag list is what makes
    // table rows different heights.
    <span className="flex gap-1 overflow-hidden">
      {names.slice(0, max).map((t) => (
        <Link
          key={t}
          to={`/problems?topic=${encodeURIComponent(t)}`}
          className="chip max-w-[9rem] shrink-0 truncate whitespace-nowrap"
        >
          {t}
        </Link>
      ))}
      {names.length > max && (
        <span className="chip shrink-0 border-transparent bg-transparent">+{names.length - max}</span>
      )}
    </span>
  )
}

/**
 * Trust, shown as a number rather than implied.
 *
 * A corpus row came from LeetCode and is simply a fact, so it says nothing —
 * a "100%" badge on 1,124 rows would train people to ignore the badge. Only
 * community rows, which are inferences until corroborated, carry one.
 */
export function Confidence({ problem }: { problem: Pick<ProblemSummary, 'origin' | 'confidence' | 'contribution_count'> }) {
  if (problem.origin !== 'community') return null
  const pct = Math.round(problem.confidence * 100)
  return (
    <span
      className="ml-2 inline-flex items-baseline gap-1.5 border border-amberEarth/40 bg-amberEarth/10 px-1.5 py-0.5"
      title={`Described by ${problem.contribution_count} ${problem.contribution_count === 1 ? 'person' : 'people'}. Confidence rises with each independent account.`}
    >
      <span className="num font-mono text-micro text-medium">{pct}%</span>
      <span className="text-micro text-medium">community</span>
    </span>
  )
}

export function title(slug: string) {
  return slug.replace(/(^|[\s-])\w/g, (c) => c.toUpperCase()).replace(/-/g, ' ')
}


/**
 * Topics as text rather than chips, for table rows.
 *
 * A bordered chip needs horizontal room it does not get in a 22%-wide column —
 * boxes were clipping mid-word ("Depth-First Sea"). As plain mono text the cell
 * truncates gracefully at the comma, and it scans the same way the "asked at"
 * column does, which is what a reader is actually comparing.
 */
export function TopicsInline({ names, max = 2 }: { names: string[]; max?: number }) {
  if (!names.length) return <span className="text-faint">—</span>
  const rest = names.length - max
  return (
    <span className="block truncate font-mono text-micro text-muted">
      {names.slice(0, max).join(' · ')}
      {rest > 0 && <span className="text-faint"> +{rest}</span>}
    </span>
  )
}
