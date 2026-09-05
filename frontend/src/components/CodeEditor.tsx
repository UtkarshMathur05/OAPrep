// Monaco wrapper.
import Editor from '@monaco-editor/react'

interface Props {
  value: string
  language: string
  onChange: (value: string) => void
}

export default function CodeEditor({ value, language, onChange }: Props) {
  return (
    <Editor
      height="420px"
      language={language}
      value={value}
      onChange={(v) => onChange(v ?? '')}
      options={{ minimap: { enabled: false }, fontSize: 14 }}
    />
  )
}
