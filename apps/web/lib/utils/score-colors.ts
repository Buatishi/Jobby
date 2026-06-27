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
