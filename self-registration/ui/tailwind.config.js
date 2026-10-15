/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"], // Specifies the files Tailwind should scan for class names
  theme: {
    extend: {
      backgroundImage: {
       'banner_bg': "url('./assets/nav_bg.png')",
      }
    }, // Allows you to customize the default theme (colors, fonts, etc.)
  },
  plugins: [], // Placeholder for any Tailwind plugins you might want to add

};
