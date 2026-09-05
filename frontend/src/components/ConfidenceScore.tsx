interface Props {
  value: number
  /** `bar` for lists and tables, `figure` for the single headline reading. */
  variant?: 'bar' | 'figure'
}

/** Confidence, 0–1. The bar is measured, not decorative: a weak match should
 *  look weak at a glance rather than reading as a full-width chip. */
export default function ConfidenceScore({ value, variant = 'bar' }: Props) {
  const pct = Math.round((value ?? 0) * 100)
  // Low confidence is amber, not red: it means "unsure", not "wrong".
  const tone = pct >= 70 ? 'bg-brownRed' : 'bg-amberEarth'

  if (variant === 'figure') {
    return (
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-3xl leading-none tabular-nums">{pct}</span>
        <span className="text-sm text-muted">% match</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-16 bg-rule" role="presentation">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-9 font-mono text-sm tabular-nums text-right">{pct}%</span>
    </div>
  )
}
