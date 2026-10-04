import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#171717",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0, 0, 0, 0.04)",
      },
    },
  },
  plugins: [],
} satisfies Config;
