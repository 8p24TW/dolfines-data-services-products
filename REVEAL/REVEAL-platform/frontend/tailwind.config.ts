import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0B2A3D",
          light: "#003366",
          dark: "#001a2a",
        },
        orange: {
          DEFAULT: "#F39200",
          accent: "#F07820",
        },
        success: "#70AD47",
        warning: "#C98A00",
        danger: "#C62828",
      },
      fontFamily: {
        sans: ["Open Sans", "Aptos", "Calibri", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
