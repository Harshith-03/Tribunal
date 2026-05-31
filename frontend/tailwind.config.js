/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F7F4EF", // warm paper
        paper: "#FFFFFF",
        ink: "#1A1714", // near-black
        soft: "#3D362F", // secondary text
        muted: "#8A8174", // tertiary / labels
        line: "#E2DCD1", // hairline
        oxblood: "#7B2D26", // primary accent
        oxbloodSoft: "#A8584F",
        teal: "#0F6E63", // secondary accent
        gold: "#B7791F",
        good: "#3F7D58",
        warn: "#9A6B16",
        bad: "#A1322B",
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        kicker: "0.18em",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(26,23,20,0.04), 0 8px 24px rgba(26,23,20,0.05)",
        lift: "0 2px 4px rgba(26,23,20,0.06), 0 18px 40px rgba(26,23,20,0.09)",
      },
    },
  },
  plugins: [],
};
