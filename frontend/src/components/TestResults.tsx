import type { VerifyResponse } from '../types'

export default function TestResults({ result }: { result: VerifyResponse }) {
  const passed = result.status === 'Accepted' && result.total > 0
  const failing = (result.results ?? []).find((r) => !r.passed)

  return (
    <div className="border border-ruleStrong bg-surface">
      <div className={`flex flex-wrap items-baseline justify-between gap-3 border-l-4 px-4 py-3
                      ${passed ? 'border-l-brownRed' : 'border-l-amberEarth'}`}>
        <span className="font-medium">{result.status}</span>
        <span className="font-mono text-sm tabular-nums text-muted">
          {result.passed}/{result.total} passed
          {result.runtime && ` · ${result.runtime}`}
          {result.memory && ` · ${result.memory}`}
        </span>
      </div>

      {failing && (
        <div className="border-t border-rule px-4 py-3">
          <p className="mb-2 text-sm text-muted">First failing case</p>
          <dl className="grid gap-2 font-mono text-sm sm:grid-cols-[5rem_1fr]">
            <dt className="text-muted">Input</dt>
            <dd className="whitespace-pre-wrap break-all">{failing.input}</dd>
            <dt className="text-muted">Expected</dt>
            <dd className="whitespace-pre-wrap break-all">{failing.expected_output}</dd>
            <dt className="text-muted">Got</dt>
            <dd className="whitespace-pre-wrap break-all text-brownRed">
              {failing.actual_output || '(nothing)'}
            </dd>
          </dl>
        </div>
      )}
    </div>
  )
}
