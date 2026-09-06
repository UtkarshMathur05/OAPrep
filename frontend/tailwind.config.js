/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // --- Brand ---------------------------------------------------------
        // The five originals, unchanged in value. What changed is their job.
        // Cream as the whole page ground made a dense, table-driven tool read
        // like an editorial site; it is now the accent surface (hero, callouts,
        // the recall feature) against a cool near-white.
        brownRed: '#9E2B25',      // the recall feature: memory, reconstruction
        amberEarth: '#E98A15',    // live state: the timer, community confidence
        floralWhite: '#FFF8F0',   // accent ground, not the page
        prussianBlue: '#191D32',  // ink and primary action
        shadowGrey: '#1E212B',    // secondary text

        // --- Ground --------------------------------------------------------
        paper: '#FAFAFB',         // the page
        surface: '#FFFFFF',       // cards, rows, panels

        // Rules are cool greys now that the ground is cool. Not black at low
        // alpha — over a white table that greys out the text behind it.
        rule: '#E6E7EC',
        ruleStrong: '#CFD2DB',
        muted: '#63677A',
        faint: '#8B8FA3',

        // --- Difficulty ----------------------------------------------------
        // A browse UI needs these to be instantly separable at 11px. Chosen to
        // clear 4.5:1 on white and to stay distinct in greyscale.
        easy: '#1A7F5A',
        medium: '#B26A00',
        hard: '#B3261E',

        // --- Editor --------------------------------------------------------
        // The solve screen inverts: full-bleed dark, so code is the only bright
        // thing on the display.
        deep: '#12141C',
        deepPanel: '#191C26',
        deepRule: '#2B2F3D',
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
