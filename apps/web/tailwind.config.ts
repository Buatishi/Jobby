import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        card: "20px",
        panel: "24px"
      },
      boxShadow: {
        card: "0 12px 40px rgba(29, 29, 27, 0.08)",
        glow: "0 0 28px rgba(43, 212, 138, 0.6)"
      },
      fontFamily: {
        sans: ["var(--font-sans-brand)", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      keyframes: {
        marquee: {
          to: { transform: "translateX(-50%)" }
        }
      },
      animation: {
        marquee: "marquee 48s linear infinite"
      },
      colors: {
        "brand-green": "#0F6E56",
        "brand-green-light": "#DEF7EC",
        "brand-mint": "#CBEADD",
        "brand-bright": "#2BD48A",
        "brand-forest": "#06231B",
        "brand-ink": "#1D1D1B",
        "brand-line": "#DCE9E4",
        "brand-accent": "#00A884",
        "bg-dashboard": "#F8FAFA",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))"
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))"
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))"
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))"
        }
      }
    }
  },
  plugins: [tailwindcssAnimate]
};

export default config;
