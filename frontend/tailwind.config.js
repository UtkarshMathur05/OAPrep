/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // --- Ground ---------------------------------------------------------
        // An editor's chrome, anchored on the brand's own dark end: shadowGrey
        // and prussianBlue were always the bottom of this palette, so they
        // become surfaces rather than being replaced.
        ground:     '#101219',  // the page
        panel:      '#171A24',  // cards, tables, the editor's side panels
        raised:     '#1E212B',  // shadowGrey — headers, hover, hero band
        select:     '#191D32',  // prussianBlue — the selected row / active filter

        line:       '#262A36',
        lineStrong: '#343947',

        // --- Text -----------------------------------------------------------
        ink:  '#E6E8EF',  // primary. 14.8:1 on bg
        ink2: '#A2A8BC',  // secondary prose and metadata. 7.4:1
        // #6B7288 looked right but sat at 3.4:1 on a raised panel, and this
        // tone carries the 11px labels — the smallest text on the site, where
        // contrast matters most. Lifted until it clears 4.5:1 everywhere.
        ink3: '#858CA2',  // labels, counts, things you read only when looking

        // --- Accent ---------------------------------------------------------
        // One action colour, and it is the Run button's: amberEarth. Loud on a
        // dark ground, so it stays rationed to one element per screen.
        accent:    '#E98A15',
        accentDim: '#7A4A0C',
        // brownRed lifted off the floor — #9E2B25 is nearly invisible on #101219.
        brand:     '#C4483F',

        // --- Syntax ---------------------------------------------------------
        // Difficulty, pass/fail and links borrow an editor's token colours. On
        // a screen full of code this is the palette the reader is already
        // parsing, so it carries meaning instead of decorating.
        easy:   '#98C379',  // string green — also "passed"
        medium: '#E5C07B',  // constant yellow — also "uncertain"
        hard:   '#E06C75',  // error red — also "failed"
        link:   '#61AFEF',  // function blue

        // --- Legacy brand ---------------------------------------------------
        // Kept so nothing referencing them breaks. Do not use on dark surfaces.
        brownRed: '#9E2B25',
        amberEarth: '#E98A15',
        floralWhite: '#FFF8F0',
        prussianBlue: '#191D32',
        shadowGrey: '#1E212B',
      },
      fontFamily: {
        // Prose only: headlines, problem statements, paragraph copy.
        sans: ['"IBM Plex Sans"', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        // Everything structural: nav, buttons, labels, counts, table heads,
        // metadata, code. Mono as the interface chrome rather than as an accent
        // is the single choice that makes this read as a developer tool.
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo',
               'Consolas', 'monospace'],
      },

      // A real scale, ~1.22 between steps, rather than Tailwind's defaults with
      // their 24 -> 30 -> 36 gaps. Line heights tighten as size grows.
      fontSize: {
        micro: ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.01em' }],   // 11
        tiny:  ['0.75rem',   { lineHeight: '1.125rem' }],                        // 12
        small: ['0.8125rem', { lineHeight: '1.25rem' }],                         // 13
        base:  ['0.9375rem', { lineHeight: '1.6' }],                             // 15
        lede:  ['1.125rem',  { lineHeight: '1.55' }],                            // 18
        h3:    ['1.375rem',  { lineHeight: '1.3',  letterSpacing: '-0.01em' }],  // 22
        h2:    ['1.75rem',   { lineHeight: '1.22', letterSpacing: '-0.015em' }], // 28
        h1:    ['2.25rem',   { lineHeight: '1.12', letterSpacing: '-0.02em' }],  // 36
        display: ['2.875rem', { lineHeight: '1.04', letterSpacing: '-0.025em' }],// 46
      },

      // Section rhythm. Bands are separated by a hairline rule and share one
      // vertical measure, so the page has a pulse instead of ad-hoc margins.
      spacing: {
        band: '4.5rem',      // 72 — desktop band padding
        'band-sm': '2.5rem', // 40 — mobile
      },

      maxWidth: {
        // 1180: wide enough for the six-column problem table, narrow enough
        // that the table's last column is not a hike from its first.
        shell: '73.75rem',
        reading: '68ch',
      },
      keyframes: {
        rise: { '0%': { opacity: '0', transform: 'translateY(6px)' },
                '100%': { opacity: '1', transform: 'none' } },
      },
      animation: {
        // One entrance, used on step changes only. Not on every card.
        rise: 'rise .28s cubic-bezier(.2,.7,.3,1) both',
      },
    },
  },
  plugins: [],
}
