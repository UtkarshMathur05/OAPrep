// Judge0 verification summary.
import type { VerifyResponse } from '../types'

export default function TestResults({ result }: { result: VerifyResponse }) {
  return (
    <div className="rounded border p-3">
      <p className="font-medium">{result.status}</p>
      <p className="text-sm">
        {result.passed}/{result.total} passed · {result.runtime} · {result.memory}
      </p>
    </div>
  )
}
