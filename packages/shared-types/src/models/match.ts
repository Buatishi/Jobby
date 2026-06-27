export type GapOrigin = "skills" | "seniority" | "both" | "none";
export type JobMatchScoreBand = "low" | "medium" | "high";

export interface ScoreBreakdown {
  skills: number;
  seniority: number;
  languages: number;
  education: number;
  company: number;
  softSkills: number;
}

export interface MatchRecommendation {
  title: string;
  description: string;
  priority: "low" | "medium" | "high";
}

export interface JobMatch {
  id: string;
  userId: string;
  profileId: string;
  jobId: string;
  matchScore: number | null;
  potentialScore: number | null;
  representationScore: number | null;
  gapOrigin: GapOrigin | null;
  scoreBreakdown: ScoreBreakdown | null;
  recommendations: MatchRecommendation[] | null;
  userRating: number | null;
  aiModelUsed: string | null;
  createdAt: string;
}
