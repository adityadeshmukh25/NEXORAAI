
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          950: "#080b12",
          900: "#0d111b",
          800: "#151b28",
          700: "#20293a",
        },
        accent: {
          DEFAULT: "#8b5cf6",
          light: "#a78bfa",
        },
      },
    },
  },
  plugins: [],
};
