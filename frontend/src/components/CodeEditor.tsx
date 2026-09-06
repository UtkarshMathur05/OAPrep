import Editor from '@monaco-editor/react'
import { MEMOIZE_DARK, defineTheme } from '../lib/monacoTheme'

interface Props {
  value: string
  language: string
  onChange: (value: string) => void
}

export default function CodeEditor({ value, language, onChange }: Props) {
  return (
    <div className="h-[500px] border-x-2 border-b-2 border-lineStrong bg-ground">
      <Editor
        height="100%"
        language={language}
        value={value}
        theme={MEMOIZE_DARK}
        beforeMount={defineTheme}
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

