export interface CompatibilityArea {
  name: string;
  score: number;
  notes: string;
}

export interface Strength {
  title: string;
  evidence: string;
}

export interface Risk {
  title: string;
  mitigation: string;
}

export interface ModelAnswer {
  question: string;
  answer: string;
  evaluationCriteria: string[];
}

export interface ActionPlan {
  title: string;
  steps: string[];
}

export interface InterviewKit {
  id: string;
  userId: string;
  profileId: string;
  jobId: string;
  matchId: string | null;
  title: string | null;
  compatibilityAreas: CompatibilityArea[];
  strengths: Strength[];
  risks: Risk[];
  modelAnswers: ModelAnswer[];
  actionPlan: ActionPlan | null;
  aiModelUsed: string | null;
  createdAt: string;
  updatedAt: string;
}
