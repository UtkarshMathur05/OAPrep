import { useEffect, useRef, useState } from 'react'

/**
 * Elapsed-time clock for the solve screen.
 *
 * Counts up rather than down. A countdown invents a deadline nobody set and
 * turns practice into a failure state at 00:00; counting up answers the
 * question people actually ask afterwards — "how long did that take me?"
 *
 * Ticks off wall-clock deltas, not accumulated setInterval calls, so a
 * backgrounded tab does not silently lose minutes.
 */
export default function Timer({ className = '' }: { className?: string }) {
  const [elapsed, setElapsed] = useState(0)
  const [running, setRunning] = useState(true)
  const anchor = useRef({ at: Date.now(), base: 0 })

  useEffect(() => {
    if (!running) return
    anchor.current = { at: Date.now(), base: elapsed }
    const id = setInterval(() => {
      setElapsed(anchor.current.base + Math.floor((Date.now() - anchor.current.at) / 1000))
    }, 250)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running])

  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0')
  const ss = String(elapsed % 60).padStart(2, '0')

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span
        className={`num font-mono text-sm ${running ? 'text-amberEarth' : 'text-faint'}`}
        aria-label={`Elapsed time ${mm} minutes ${ss} seconds`}
      >
        {mm}:{ss}
      </span>
      <button
        onClick={() => setRunning((r) => !r)}
        className="text-micro text-faint underline-offset-2 hover:text-white hover:underline"
      >
        {running ? 'Pause' : 'Resume'}
      </button>
    </div>
  )
}
