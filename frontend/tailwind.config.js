/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  theme: {
    extend: {
      colors: {
        brownRed: '#9E2B25',
        amberEarth: '#E98A15',
        floralWhite: '#FFF8F0',
        prussianBlue: '#191D32',
        shadowGrey: '#1E212B',
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', "Liberation Mono", "Courier New", 'monospace'],
      },
    },
  },
  plugins: [],
}
