/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Palette (unchanged)
        brownRed: '#9E2B25',
        amberEarth: '#E98A15',
        floralWhite: '#FFF8F0',
        prussianBlue: '#191D32',
        shadowGrey: '#1E212B',

        // Derived tones. Rules are warm greys mixed from the paper, not
        // black-at-low-alpha — on a cream ground that reads muddy.
        rule: '#E7DCCD',
        ruleStrong: '#D6C7B4',
        surface: '#FFFFFF',
        muted: '#6B6357',
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        // Mono is for data the user reads as data: match scores, topics, test
        // I/O, code. Not for decoration.
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas',
               'Liberation Mono', 'Courier New', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      maxWidth: {
        reading: '68ch',
      },
    },
  },
  plugins: [],
}
