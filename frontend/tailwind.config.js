/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'vajra': {
          'cyan': '#00bcd4',
          'purple': '#9c27b0',
          'deep-purple': '#673ab7',
          'indigo': '#3f51b5',
          'blue': '#2196f3',
          'teal': '#009688',
          'green': '#4caf50',
          'yellow': '#ffeb3b',
          'orange': '#ff9800',
          'red': '#f44336',
          'pink': '#e91e63',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 8s linear infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        }
      }
    },
  },
  plugins: [],
}