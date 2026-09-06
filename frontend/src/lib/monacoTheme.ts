import type { Monaco } from '@monaco-editor/react'

/**
 * The editor, painted in the site's own ramp.
 *
 * Monaco's stock `vs-dark` sits on #1E1E1E, a different dark grey from every
 * panel around it — the editor read as a window pasted onto the page rather
 * than part of it. The token colours are the same ones the rest of the site
 * uses for difficulty, pass/fail and links, so a keyword and an "easy" tag are
 * literally the same green.
 */
export const MEMOIZE_DARK = 'memoize-dark'

export function defineTheme(monaco: Monaco) {
  monaco.editor.defineTheme(MEMOIZE_DARK, {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: '', foreground: 'E6E8EF' },
      { token: 'comment', foreground: '858CA2', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'E98A15' },
      { token: 'string', foreground: '98C379' },
      { token: 'number', foreground: 'E5C07B' },
      { token: 'type', foreground: '61AFEF' },
      { token: 'function', foreground: '61AFEF' },
      { token: 'variable', foreground: 'E6E8EF' },
      { token: 'delimiter', foreground: 'A2A8BC' },
    ],
    colors: {
      'editor.background': '#101219',
      'editor.foreground': '#E6E8EF',
      'editorLineNumber.foreground': '#4B5266',
      'editorLineNumber.activeForeground': '#A2A8BC',
      'editor.lineHighlightBackground': '#171A24',
      'editor.selectionBackground': '#191D32',
      'editorCursor.foreground': '#E98A15',
      'editorIndentGuide.background1': '#262A36',
      'editorIndentGuide.activeBackground1': '#343947',
      'editorWidget.background': '#171A24',
      'editorWidget.border': '#343947',
      'scrollbarSlider.background': '#34394780',
      'scrollbarSlider.hoverBackground': '#343947',
      'scrollbarSlider.activeBackground': '#858CA2',
    },
  })
}
