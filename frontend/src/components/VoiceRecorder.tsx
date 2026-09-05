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
    <div className="space-y-6">
      <div className="relative border-2 border-prussianBlue bg-white">
        <textarea
          className="w-full p-6 min-h-[200px] resize-none outline-none text-prussianBlue bg-transparent text-lg"
          placeholder="e.g. I remember a problem about a grid where you had to move right or down..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {SR && (
          <div className="absolute bottom-4 right-4">
            <button
              onClick={toggleRecording}
              className={`px-4 py-2 text-sm font-bold tracking-wide uppercase border-2 transition-colors ${
                isRecording 
                  ? 'border-brownRed bg-brownRed text-floralWhite animate-pulse' 
                  : 'border-prussianBlue text-prussianBlue hover:bg-prussianBlue/5'
              }`}
            >
              {isRecording ? 'Listening...' : 'Dictate'}
            </button>
          </div>
        )}
      </div>
      
      <button
        className="bg-brownRed text-floralWhite px-8 py-4 font-bold uppercase tracking-widest disabled:opacity-50 hover:bg-[#8A2520] transition-colors"
        disabled={loading || !text.trim()}
        onClick={() => onSubmit(text)}
      >
        {loading ? 'Processing...' : 'Analyze Memory'}
      </button>
    </div>
  )
}

