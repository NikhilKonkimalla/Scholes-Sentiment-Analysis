/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
      },
      colors: {
        gold: {
          DEFAULT: '#CCA754',
          light: '#D4AF37',
          dark: '#B8962E',
        },
        surface: {
          DEFAULT: '#1C1E20',
          light: '#25282B',
          dark: '#141618',
        },
        accent: {
          green: '#10b981',
          red: '#f43f5e',
        },
      },
    },
  },
  plugins: [],
}
