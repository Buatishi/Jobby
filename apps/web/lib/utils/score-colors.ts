import type { JobMatchScoreBand } from "@jobmatch/shared-types";

export const scoreColors = {
  red: "#E24B4A",
  yellow: "#F0A500",
  lightGreen: "#1D9E75",
  darkGreen: "#0F6E56"
} as const;

export const scoreColorClasses: Record<JobMatchScoreBand, string> = {
  low: "text-destructive",
  medium: "text-primary",
  high: "text-secondary"
};

export function getScoreColor(score: number): string {
  if (score <= 40) {
    return scoreColors.red;
  }

  if (score <= 65) {
    return scoreColors.yellow;
  }

  if (score <= 80) {
    return scoreColors.lightGreen;
  }

  return scoreColors.darkGreen;
}

export function getScoreLabel(score: number): string {
  if (score <= 40) {
    return "Bajo";
  }

  if (score <= 65) {
    return "Medio";
  }

  if (score <= 80) {
    return "Alto";
  }

  return "Excelente";
}

// Sobre paneles oscuros el verde oscuro casi no contrasta: las dos bandas verdes
// se muestran con el verde vivo de la marca. Rojo y amarillo ya se leen bien.
export const scoreColorOnDarkGreen = "#2BD48A";

export function getScoreColorOnDark(score: number): string {
  const color = getScoreColor(score);

  if (color === scoreColors.lightGreen || color === scoreColors.darkGreen) {
    return scoreColorOnDarkGreen;
  }

  return color;
}

export type StatusTone = "ok" | "mid" | "bad";

// Colores de los estados "cumple / parcial / falta" para píldoras, en superficie clara y oscura.
export const statusTones = {
  light: {
    ok: { background: "#CBEADD", color: "#0F6E56" },
    mid: { background: "#FFF1D6", color: "#8A5300" },
    bad: { background: "#FCE4E2", color: "#8E2B26" }
  },
  dark: {
    ok: { background: "rgba(43, 212, 138, 0.16)", color: "#7FE9BD" },
    mid: { background: "rgba(224, 138, 0, 0.18)", color: "#FFC46B" },
    bad: { background: "rgba(201, 74, 68, 0.2)", color: "#FF9A94" }
  }
} as const;
