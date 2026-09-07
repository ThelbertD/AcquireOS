import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Light, neutral. One accent, used sparingly so it still means something.
        ink: {
          DEFAULT: '#16181d',
          soft: '#3d4451',
          muted: '#6b7280',
          faint: '#9aa1ad',
        },
        paper: {
          DEFAULT: '#ffffff',
          sunk: '#f7f8fa',
          rail: '#fbfcfd',
        },
        edge: {
          DEFAULT: '#e3e6ec',
          soft: '#eef0f4',
          strong: '#cfd4de',
        },
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          400: '#818cf8',
          500: '#5b6ef5',
          600: '#4a56e0',
          700: '#3b45b8',
        },
        good: { bg: '#effaf4', line: '#b6e3cd', text: '#12684a' },
        warn: { bg: '#fff8ec', line: '#f3ddb0', text: '#8a5a10' },
        bad: { bg: '#fdf1f1', line: '#f1c4c4', text: '#98262a' },
      },
      fontFamily: {
        sans: [
          'ui-sans-serif', '-apple-system', 'Segoe UI', 'Inter', 'Roboto',
          'Helvetica Neue', 'Arial', 'sans-serif',
        ],
        mono: [
          'ui-monospace', 'Cascadia Code', 'JetBrains Mono', 'Consolas',
          'Liberation Mono', 'monospace',
        ],
      },
      fontSize: {
        // A step up from Tailwind's defaults throughout — the previous build read small.
        xs: ['0.8125rem', { lineHeight: '1.15rem' }],
        sm: ['0.9063rem', { lineHeight: '1.35rem' }],
        base: ['1.0313rem', { lineHeight: '1.65rem' }],
        lg: ['1.1563rem', { lineHeight: '1.75rem' }],
        xl: ['1.3125rem', { lineHeight: '1.85rem' }],
        '2xl': ['1.625rem', { lineHeight: '2.1rem' }],
        '3xl': ['2.0625rem', { lineHeight: '2.45rem' }],
      },
      borderRadius: { xl: '0.75rem', '2xl': '1rem' },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06)',
        lift: '0 4px 12px rgba(16,24,40,.08), 0 2px 4px rgba(16,24,40,.04)',
      },
    },
  },
  plugins: [],
}

export default config
