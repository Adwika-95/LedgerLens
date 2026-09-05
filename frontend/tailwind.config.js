/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#FAF9F6',
        ink: '#1C1917',
        steel: '#6B7280',
        line: '#E7E3DC',
        amber: {
          DEFAULT: '#B45309',
          soft: '#FEF3E2',
        },
        teal: {
          DEFAULT: '#0F766E',
          soft: '#ECFAF8',
        },
      },
      fontFamily: {
        serif: ['"Newsreader"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
