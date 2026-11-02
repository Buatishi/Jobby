export type RealityGapSkill = {
  skill_id: string | null;
  name: string;
  category: string | null;
  // null cuando el documento falta o todavía no se leyó: no hay con qué comparar.
  in_cv: boolean | null;
  in_linkedin: boolean | null;
  // false en una skill que solo nombra un documento (por ejemplo, solo LinkedIn).
  saved: boolean;
  confirmed: boolean;
  rejected: boolean;
  coherence_score: number | null;
  recommendation: string | null;
};

export type RealityGapDocument = {
  filename: string | null;
  uploaded_at: string | null;
  status: string | null;
  // "saved": CV leído antes de guardar su lista propia de skills.
  skills_source: "document" | "saved" | null;
};

export type RealityGapSummary = {
  comparable: boolean;
  total: number;
  in_both: number;
  only_cv: number;
  only_linkedin: number;
  in_neither: number;
  score: number | null;
};

export type RealityGapReport = {
  profile_id: string;
  skills: RealityGapSkill[];
  summary: RealityGapSummary;
  cv: RealityGapDocument | null;
  linkedin: RealityGapDocument | null;
};
