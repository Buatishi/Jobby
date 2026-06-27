export type SkillCategory = "technical" | "soft" | "language" | "domain";
export type SkillLevel = "beginner" | "intermediate" | "advanced" | "expert";
export type WorkModality = "remote" | "hybrid" | "onsite";
export type Seniority = "junior" | "mid" | "senior" | "staff" | "principal";

export interface MasterProfile {
  id: string;
  userId: string;
  headline: string | null;
  summary: string | null;
  targetRole: string | null;
  targetSeniority: Seniority | null;
  workModality: WorkModality | null;
  targetIndustry: string[] | null;
  linkedinUrl: string | null;
  completenessPct: number;
  inferredSoftSkills: string[];
  softSkillsComputedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Skill {
  id: string;
  profileId: string;
  name: string;
  category: SkillCategory | null;
  level: SkillLevel | null;
  inCv: boolean;
  inLinkedin: boolean;
  confirmed: boolean;
  createdAt: string;
}

export interface Experience {
  id: string;
  profileId: string;
  company: string;
  title: string;
  startedAt: string | null;
  endedAt: string | null;
  isCurrent: boolean;
  description: string | null;
  achievements: string[] | null;
  createdAt: string;
}

export interface Education {
  id: string;
  profileId: string;
  institution: string;
  fieldOfStudy: string | null;
  degreeLevel: string | null;
  startedAt: string | null;
  endedAt: string | null;
  isOngoing: boolean;
  createdAt: string;
}

export interface Language {
  id: string;
  profileId: string;
  name: string;
  proficiency: string | null;
  createdAt: string;
}

export interface Certification {
  id: string;
  profileId: string;
  name: string;
  issuer: string | null;
  issuedAt: string | null;
  expiresAt: string | null;
  credentialUrl: string | null;
  createdAt: string;
}
