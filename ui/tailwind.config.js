/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        anthropic: {
          'ivory-light': '#faf9f5',
          'ivory-medium': '#f0eee6',
          'slate-dark': '#141413',
          'cloud-medium': '#b0aea5',
          'cloud-dark': '#87867f',
          'oat': '#e3dacc',
          'accent': '#c6613f',
          'clay': '#d97757',
        },
      },
      fontFamily: {
        serif: ['Newsreader', 'Anthropic Serif', 'Georgia', 'serif'],
        sans: ['Inter', 'Anthropic Sans', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Anthropic Mono', 'Menlo', 'monospace'],
      },
      borderRadius: {
        'small': '0.25rem',
        'main': '0.5rem',
        'large': '1rem',
        'xl': '1.5rem',
        'round': '9999px',
      },
      boxShadow: {
        'anthropic': '0px 2px 4px rgba(20, 20, 19, 0.04)',
        'anthropic-hover': '0 6px 20px -4px rgba(20, 20, 19, 0.08)',
      },
    },
  },
  plugins: [],
}
