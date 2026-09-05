export default function ConfidenceScore({ value }: { value: number }) {
  const percentage = Math.round(value * 100)
  return (
    <div className="flex flex-col items-end">
      <span className="text-xl font-bold font-mono text-prussianBlue mb-1">{percentage}%</span>
      <div className="w-full h-1.5 bg-shadowGrey/10">
        <div className="h-full bg-brownRed" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

