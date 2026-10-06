export type DashboardMatch = {
  id: string;
  company?: string | null;
  company_name?: string | null;
  role?: string | null;
  title?: string | null;
  job_title?: string | null;
  score?: number | null;
  match_score?: number | null;
  created_at?: string | null;
  analyzed_at?: string | null;
};

export type DashboardSummary = {
  user_name?: string | null;
  full_name?: string | null;
  email?: string | null;
  user_email?: string | null;
  name?: string | null;
  employability_score?: number | null;
  global_score?: number | null;
  completeness_pct?: number | null;
  completeness?: number | null;
  missing_tip?: string | null;
  most_valuable_missing_field?: string | null;
  latest_matches?: DashboardMatch[] | null;
  matches?: DashboardMatch[] | null;
};

export function clampScore(value: number | null | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }

  return Math.max(0, Math.min(100, Math.round(value)));
}

export function getFirstName(summary: DashboardSummary | undefined): string {
  const fullName = summary?.full_name?.trim();
  if (fullName) {
    return fullName.split(/\s+/)[0] ?? "";
  }

  const rawName =
    summary?.email ?? summary?.user_email ?? summary?.user_name ?? summary?.name ?? "";
  const cleanName = rawName.includes("@") ? (rawName.split("@")[0] ?? "") : rawName;

  return cleanName.trim().split(/\s+/)[0] ?? "";
}

// Iniciales para el cuadrito de cada match: empresa o, si falta, el puesto.
export function getInitials(...names: Array<string | null | undefined>): string {
  const source = names.find((name) => name && name.trim()) ?? "";
  const words = source.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) {
    return "?";
  }

  const letters =
    words.length === 1 ? words[0]!.slice(0, 2) : `${words[0]![0]}${words[1]![0]}`;

  return letters.toUpperCase();
}
