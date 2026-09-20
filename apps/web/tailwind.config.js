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
        nexus: {
          bg: '#0a0f1a',
          surface: '#111827',
          surfaceHover: '#1a2238',
          border: '#2a3550',
          borderHover: '#3a4a6e',
          text: '#e8edf5',
          textMuted: '#8b98b8',
          primary: '#2563eb',
          primaryHover: '#1d4ed8',
          primaryLight: '#1e3a5f',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
          info: '#3b82f6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}