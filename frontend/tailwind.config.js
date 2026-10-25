/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        pastel: {
          bg: '#FAF9FC',
          surface: '#FFFFFF',
          lavenderPale: '#ECECFA',
          blush: '#F7E8F5',
          powderBlue: '#E3EEFF',
          primary: '#7664E8',
          text: '#171A35',
          muted: '#737895',
          border: '#DFE1F2',
        },
        research: {
          bg: '#FAF9FC',
          primary: '#7664E8',
          secondary: '#6BA1F5',
          text: '#171A35',
          muted: '#737895',
          glow: 'rgba(118, 100, 232, 0.22)',
        },
        coding: {
          bg: '#FAF9FC',
          primary: '#7664E8',
          secondary: '#E68FC4',
          text: '#171A35',
          muted: '#737895',
          glow: 'rgba(230, 143, 196, 0.22)',
        },
        deploy: {
          bg: '#FAF9FC',
          primary: '#7664E8',
          secondary: '#6BA1F5',
          text: '#171A35',
          muted: '#737895',
          glow: 'rgba(107, 161, 245, 0.22)',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
};
