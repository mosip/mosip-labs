/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "on-page": "var(--color-on-page)",
        page: "var(--color-page)",
        surface: "var(--color-surface)",
        "panel-border": "var(--color-panel-border)",
        brand: {
          DEFAULT: "var(--color-brand)",
          hover: "var(--color-brand-hover)",
          light: "var(--color-brand-light)",
          mid: "var(--color-brand-mid)",
          dark: "var(--color-brand-dark)",
          ink: "var(--color-brand-ink)",
          soft: "var(--color-brand-soft)",
          softer: "var(--color-brand-softer)",
          featured: "var(--color-brand-featured)",
          blob: "var(--color-brand-blob)",
          muted: "var(--color-on-header-muted)",
        },
        pr: {
          DEFAULT: "var(--color-pr)",
          fill: "var(--color-pr-fill)",
          text: "var(--color-pr-text)",
          blob: "var(--color-pr-blob)",
        },
        review: {
          DEFAULT: "var(--color-review)",
          fill: "var(--color-review-fill)",
          text: "var(--color-review-text)",
          ink: "var(--color-review-ink)",
          blob: "var(--color-review-blob)",
        },
        issue: {
          DEFAULT: "var(--color-issue)",
          fill: "var(--color-issue-fill)",
          text: "var(--color-issue-text)",
          ink: "var(--color-issue-ink)",
          blob: "var(--color-issue-blob)",
        },
        csv: {
          DEFAULT: "var(--color-csv)",
          hover: "var(--color-csv-hover)",
        },
        up: "var(--color-up)",
        down: "var(--color-down)",
        orb: {
          1: "var(--color-orb-1)",
          2: "var(--color-orb-2)",
          3: "var(--color-orb-3)",
        },
        avatar: {
          1: "var(--color-avatar-1)",
          2: "var(--color-avatar-2)",
          3: "var(--color-avatar-3)",
          4: "var(--color-avatar-4)",
          5: "var(--color-avatar-5)",
          6: "var(--color-avatar-6)",
        },
      },
    },
  },
  plugins: [],
};
