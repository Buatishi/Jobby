export interface JobDescription {
  id: string;
  userId: string;
  sourceUrl: string | null;
  rawText: string | null;
  jobTitle: string | null;
  companyName: string | null;
  requiredSeniority: string | null;
  requiredModality: string | null;
  industry: string | null;
  techStack: string[] | null;
  requiredSkills: Record<string, unknown> | null;
  softSkills: string[] | null;
  requiredEducation: string | null;
  requiredLanguages: Record<string, unknown> | null;
  salaryMin: number | null;
  salaryMax: number | null;
  currency: string | null;
  createdAt: string;
}

export interface JobAnalysisRequest {
  sourceUrl?: string;
  rawText?: string;
}
