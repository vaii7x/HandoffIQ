/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        research: {
          bg: '#050A12',
          primary: '#78BFFF',
          secondary: '#377FEA',
          text: '#F4F7FC',
          muted: '#8D9BB0',
          glow: 'rgba(120, 191, 255, 0.4)',
        },
        coding: {
          bg: '#0B0804',
          primary: '#FFC15C',
          secondary: '#D98A24',
          text: '#FFF8EC',
          muted: '#A99B87',
          glow: 'rgba(255, 193, 92, 0.4)',
        },
        deploy: {
          bg: '#031013',
          primary: '#73F4F5',
          secondary: '#16BFC8',
          text: '#F0FFFF',
          muted: '#8AAEB2',
          glow: 'rgba(115, 244, 245, 0.4)',
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
