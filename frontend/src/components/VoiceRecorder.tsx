import { useState, useRef, useEffect } from 'react'

interface Props {
  onSubmit: (transcript: string) => void
  loading?: boolean
  /** Seeds the field from outside — the example memories on /recall. Changing
   *  it replaces whatever is typed, which is what picking an example means. */
  seed?: string
}

export default function VoiceRecorder({ onSubmit, loading, seed }: Props) {
  const [text, setText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  
  const SR = (window as any).webkitSpeechRecognition ?? (window as any).SpeechRecognition
  const recognitionRef = useRef<any>(null)
  
  useEffect(() => {
    if (SR) {
      recognitionRef.current = new SR()
      recognitionRef.current.continuous = true
      recognitionRef.current.interimResults = true
      
      recognitionRef.current.onresult = (event: any) => {
        let currentTranscript = ''
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            currentTranscript += event.results[i][0].transcript + ' '
          }
        }
        if (currentTranscript) {
          setText(prev => prev + currentTranscript)
        }
      }
      
      recognitionRef.current.onend = () => {
        setIsRecording(false)
      }
    }
  }, [SR])
  
  useEffect(() => {
    if (seed) setText(seed)
  }, [seed])

  const toggleRecording = () => {
    if (!recognitionRef.current) return
    if (isRecording) {
      recognitionRef.current.stop()
      setIsRecording(false)
    } else {
      recognitionRef.current.start()
      setIsRecording(true)
    }
  }

  const submit = () => {
    if (text.trim() && !loading) onSubmit(text)
  }

  // Same field as the landing hero, deliberately: arriving at /recall from the
  // landing should feel like the same box followed you, not like a second form.
  return (
    <div className="border border-lineStrong bg-panel transition-colors focus-within:border-accent">
      <div className="flex gap-3 px-4 pt-4">
        <span aria-hidden className="select-none font-mono text-base text-accent">&gt;</span>
        <textarea
          className="min-h-[8rem] w-full resize-none bg-transparent text-base leading-relaxed
                     outline-none placeholder:text-ink3"
          placeholder="there was a grid, you could only move right or down, and you had to make some total as small as possible. I think there were obstacles?"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
          }}
        />
      </div>

      <div className="mt-2 flex items-center justify-between gap-3 border-t border-line px-3 py-2">
        {SR ? (
          <button
            type="button"
            onClick={toggleRecording}
            aria-pressed={isRecording}
            className={`flex min-h-6 items-center gap-2 px-1 font-mono text-micro transition-colors
              focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent
              ${isRecording ? 'text-accent' : 'text-ink3 hover:text-ink'}`}
          >
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${
              isRecording ? 'animate-pulse bg-accent' : 'bg-lineStrong'}`} />
            {isRecording ? 'listening — tap to stop' : 'speak instead'}
          </button>
        ) : (
          <span className="font-mono text-micro text-ink3">⌘↵ to search</span>
        )}

        <button className="btn-accent" disabled={loading || !text.trim()} onClick={submit}>
          {loading ? 'reading your memory…' : 'recall it'}
        </button>
      </div>
    </div>
  )
}
