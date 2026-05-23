/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        slate: {
          50:  '#faf9f6',
          100: '#f1ede5',
          200: '#e9e5dd',
          300: '#d8d0c5',
          400: '#938b7f',
          500: '#7a7268',
          600: '#56514a',
          700: '#3a3630',
          800: '#2e2b26',
          900: '#1c1a17',
          950: '#0f0e0c',
        },
        card: '#ffffff',
        accent: {
          DEFAULT: '#e0533d',
          deep:    '#c1402c',
          soft:    '#fdeee9',
        },
      },
      fontFamily: {
        sans:  ['Public Sans', 'system-ui', 'sans-serif'],
        serif: ['Fraunces', 'Georgia', 'serif'],
        mono:  ['Spline Sans Mono', 'Menlo', 'monospace'],
      },
      maxWidth: {
        app: '67.5rem', // 1080px
      },
      boxShadow: {
        card: '0 1px 2px rgba(40,32,22,.06)',
        'card-hover': '0 8px 24px -10px rgba(40,32,22,.12)',
      },
    },
  },
  plugins: [],
};
