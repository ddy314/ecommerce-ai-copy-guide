/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#9B87F5',
          dark: '#7C67E1',
          light: '#EDE9FE',
        },
        accent: {
          blue: '#93C5FD',
          yellow: '#FDE68A',
        },
        surface: '#FFFFFF',
        page: '#F8F8FC',
      },
      boxShadow: {
        'card': '0 4px 6px -1px rgba(155, 135, 245, 0.06), 0 10px 15px -3px rgba(155, 135, 245, 0.1)',
        'card-hover': '0 10px 15px -3px rgba(155, 135, 245, 0.1), 0 20px 25px -5px rgba(155, 135, 245, 0.12)',
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.35s ease-out forwards',
        'modal-in': 'modal-in 0.2s ease-out forwards',
        'pulse-ring': 'pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'modal-in': {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgba(155, 135, 245, 0.4)' },
          '70%': { boxShadow: '0 0 0 12px rgba(155, 135, 245, 0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(155, 135, 245, 0)' },
        },
      },
    },
  },
  plugins: [],
}
