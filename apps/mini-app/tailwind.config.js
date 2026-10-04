/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: 'var(--color-primary)',
        background: 'var(--color-background)',
        surface: 'var(--color-surface)',
        ink: 'var(--color-ink)',
        muted: 'var(--color-muted)',
        'surface-p': 'var(--color-surface-p)',
        'surface-s': 'var(--color-surface-s)',
        'surface-t': 'var(--color-surface-t)',
        'surface-n': 'var(--color-surface-n)',
      },
      fontFamily: {
        sans: ['Onest', 'sans-serif'],
      },
      borderRadius: {
        'card-1': '24px',
        'card-2': '10px',
        'btn-1': '17px',
        'btn-2': '7px',
      }
    },
  },
  plugins: [],
}
