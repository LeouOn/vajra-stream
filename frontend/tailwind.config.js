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
          'gold': '#ffd700',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 8s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'rotate-glow': 'rotate-glow 4s linear infinite',
        'particle-float': 'particle-float 10s infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        glow: {
          '0%, 100%': {
            boxShadow: '0 0 5px rgba(138, 43, 226, 0.5)',
            filter: 'brightness(1)'
          },
          '50%': {
            boxShadow: '0 0 20px rgba(138, 43, 226, 0.8), 0 0 30px rgba(138, 43, 226, 0.4)',
            filter: 'brightness(1.2)'
          },
        },
        'rotate-glow': {
          '0%': {
            filter: 'hue-rotate(0deg)',
            boxShadow: '0 0 10px rgba(138, 43, 226, 0.6)'
          },
          '50%': {
            filter: 'hue-rotate(180deg)',
            boxShadow: '0 0 20px rgba(255, 215, 0, 0.6)'
          },
          '100%': {
            filter: 'hue-rotate(360deg)',
            boxShadow: '0 0 10px rgba(138, 43, 226, 0.6)'
          }
        },
        'particle-float': {
          '0%': {
            opacity: '0',
            transform: 'translateY(100px) scale(0)'
          },
          '10%': {
            opacity: '1',
            transform: 'translateY(80px) scale(1)'
          },
          '90%': {
            opacity: '1',
            transform: 'translateY(-80px) scale(1)'
          },
          '100%': {
            opacity: '0',
            transform: 'translateY(-100px) scale(0)'
          }
        }
      },
      backdropBlur: {
        'xs': '2px',
      }
    },
  },
  plugins: [],
}