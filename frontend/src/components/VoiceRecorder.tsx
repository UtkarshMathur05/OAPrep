import { useState, useRef, useEffect } from 'react'

interface Props {
  onSubmit: (transcript: string) => void
  loading?: boolean
}

export default function VoiceRecorder({ onSubmit, loading }: Props) {
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

  return (
    <div className="space-y-4">
      <div className="border border-ruleStrong bg-surface focus-within:border-prussianBlue">
        <textarea
          className="min-h-[11rem] w-full resize-none bg-transparent p-4 outline-none
                     placeholder:text-muted"
          placeholder="There was a grid, you could only move right or down, and you had to make some total as small as possible. I think there were obstacles?"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {SR && (
          <div className="flex justify-end border-t border-rule px-3 py-2">
            <button
              type="button"
              onClick={toggleRecording}
              aria-pressed={isRecording}
              className={`flex items-center gap-2 px-2.5 py-1 text-sm transition-colors
                focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brownRed
                ${isRecording ? 'text-brownRed' : 'text-muted hover:text-prussianBlue'}`}
            >
              <span className={`inline-block h-2 w-2 rounded-full ${
                isRecording ? 'animate-pulse bg-brownRed' : 'bg-ruleStrong'}`} />
              {isRecording ? 'Listening — tap to stop' : 'Speak instead'}
            </button>
          </div>
        )}
      </div>

      <button
        className="bg-brownRed px-5 py-2.5 font-medium text-floralWhite transition-colors
                   hover:bg-[#8A2520] disabled:opacity-40
                   focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-prussianBlue"
        disabled={loading || !text.trim()}
        onClick={() => onSubmit(text)}
      >
        {loading ? 'Reading your memory…' : 'Recall this problem'}
      </button>
    </div>
  )
}
