// Confidence bar, 0..1.
export default function ConfidenceScore({ value }: { value: number }) {
  return (
    <div className="space-y-1">
      <div className="h-2 w-full rounded bg-gray-200">
        <div className="h-2 rounded bg-black" style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      <span className="text-sm">{(value * 100).toFixed(0)}% confident</span>
    </div>
  )
}
