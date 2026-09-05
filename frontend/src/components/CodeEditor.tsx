import Editor from '@monaco-editor/react'

interface Props {
  value: string
  language: string
  onChange: (value: string) => void
}

export default function CodeEditor({ value, language, onChange }: Props) {
  return (
    <div className="h-[500px] border-x-2 border-b-2 border-prussianBlue bg-[#1e1e1e]">
      <Editor
        height="100%"
        language={language}
        value={value}
        theme="vs-dark"
        onChange={(v) => onChange(v ?? '')}
        options={{ 
          minimap: { enabled: false }, 
          fontSize: 14,
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          padding: { top: 16, bottom: 16 },
          scrollBeyondLastLine: false,
          roundedSelection: false,
          hideCursorInOverviewRuler: true,
          overviewRulerBorder: false,
        }}
      />
    </div>
  )
}

