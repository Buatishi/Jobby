/** Forma de GET /api/v1/admin/metrics: solo conteos y promedios, nunca datos de una persona. */
export type DailyActivity = {
  day: string;
  cvs: number;
  jobs: number;
  matches: number;
};

export type AdminMetrics = {
  generated_at: string;
  users: {
    total: number;
    free: number;
    premium: number;
    new_last_7_days: number;
    new_last_30_days: number;
  };
  cvs: { total: number; done: number; failed: number; in_progress: number };
  jobs: { total: number; last_7_days: number };
  matches: {
    total: number;
    last_7_days: number;
    average_score: number | null;
    rated: number;
    average_rating: number | null;
  };
  interview_kits: { total: number; done: number; failed: number };
  daily_activity: DailyActivity[];
};

export type ActivitySeries = "cvs" | "jobs" | "matches";

export type ActivityBar = {
  day: string;
  value: number;
  /** Alto relativo al día con más actividad de la serie (0 a 100). */
  heightPercent: number;
  /** Solo el máximo más reciente lleva etiqueta: el resto se lee en el tooltip o la tabla. */
  isPeak: boolean;
};

export function activityBars(
  days: DailyActivity[],
  series: ActivitySeries
): ActivityBar[] {
  const max = days.reduce((highest, day) => Math.max(highest, day[series]), 0);
  const peakIndex =
    max > 0 ? days.map((day) => day[series]).lastIndexOf(max) : -1;

  return days.map((day, index) => ({
    day: day.day,
    value: day[series],
    heightPercent: max > 0 ? Math.round((day[series] / max) * 100) : 0,
    isPeak: index === peakIndex
  }));
}

export function seriesTotal(days: DailyActivity[], series: ActivitySeries): number {
  return days.reduce((total, day) => total + day[series], 0);
}

/** "2026-09-24" en el idioma de la interfaz, sin corrimiento por zona horaria. */
export function formatDay(day: string, locale: string): string {
  const [year, month, date] = day.split("-").map(Number);
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    timeZone: "UTC"
  }).format(new Date(Date.UTC(year, month - 1, date)));
}
