// Voice/text input for the user's memory.
// TODO(frontend): add Web Speech API recording; the textarea is the fallback.
import { useState } from 'react'

interface Props {
  onSubmit: (transcript: string) => void
  loading?: boolean
}

export default function VoiceRecorder({ onSubmit, loading }: Props) {
  const [text, setText] = useState('')
  return (
    <div className="space-y-2">
      <textarea
        className="w-full rounded border p-3"
        rows={4}
        placeholder="Describe the problem you half-remember..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
        disabled={loading || !text.trim()}
        onClick={() => onSubmit(text)}
      >
        {loading ? 'Thinking...' : 'Recall'}
      </button>
    </div>
  )
}
