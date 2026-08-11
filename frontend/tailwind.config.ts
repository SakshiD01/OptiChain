import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-body)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-body)", "sans-serif"],
      },
      colors: {
        ink: {
          DEFAULT: "#0f172a",
          soft: "#1e293b",
          muted: "#64748b",
        },
        accent: {
          DEFAULT: "#0f766e",
          bright: "#14b8a6",
          hover: "#0d9488",
        },
      },
      boxShadow: {
        panel:
          "0 0 0 1px rgba(15,23,42,0.04), 0 1px 2px rgba(15,23,42,0.04), 0 12px 32px rgba(15,23,42,0.06)",
      },
      animation: {
        "shiny-text": "shiny-text 3s ease-in-out infinite",
        "shimmer-slide":
          "shimmer-slide var(--speed) ease-in-out infinite alternate",
        "spin-around": "spin-around calc(var(--speed) * 2) infinite linear",
        rippling: "rippling var(--duration) ease-out",
      },
      keyframes: {
        "shiny-text": {
          "0%, 90%, 100%": {
            backgroundPosition: "calc(-100% - var(--shiny-width)) 0",
          },
          "30%, 60%": {
            backgroundPosition: "calc(100% + var(--shiny-width)) 0",
          },
        },
        "shimmer-slide": {
          to: {
            transform: "translate(calc(100cqw - 100%), 0)",
          },
        },
        "spin-around": {
          "0%": { transform: "translateZ(0) rotate(0)" },
          "15%, 35%": { transform: "translateZ(0) rotate(90deg)" },
          "65%, 85%": { transform: "translateZ(0) rotate(270deg)" },
          "100%": { transform: "translateZ(0) rotate(360deg)" },
        },
        rippling: {
          "0%": { opacity: "1" },
          "100%": { transform: "scale(2)", opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
