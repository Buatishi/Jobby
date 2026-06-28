"use client";

export type WizardStep = 1 | 2 | 3 | 4;

export type WizardSkillDraft = {
  id: string;
  name: string;
  category: string | null;
  level: string | null;
  source: string;
  confirmed?: boolean;
  rejected?: boolean;
};

export type WizardProgress = {
  currentStep: WizardStep;
  completed: boolean;
  taskId?: string;
  documentId?: string;
  parsedSkills?: WizardSkillDraft[];
};

export const WIZARD_PROGRESS_KEY = "jobmatch_wizard_progress";

const defaultProgress: WizardProgress = {
  currentStep: 1,
  completed: false
};

export function getWizardProgress(): WizardProgress {
  if (typeof window === "undefined") {
    return defaultProgress;
  }

  const rawProgress = window.localStorage.getItem(WIZARD_PROGRESS_KEY);
  if (!rawProgress) {
    return defaultProgress;
  }

  try {
    return { ...defaultProgress, ...JSON.parse(rawProgress) } as WizardProgress;
  } catch {
    return defaultProgress;
  }
}

export function hasWizardProgress() {
  if (typeof window === "undefined") {
    return false;
  }

  return window.localStorage.getItem(WIZARD_PROGRESS_KEY) !== null;
}

export function saveWizardProgress(update: Partial<WizardProgress>) {
  const nextProgress = { ...getWizardProgress(), ...update };
  window.localStorage.setItem(WIZARD_PROGRESS_KEY, JSON.stringify(nextProgress));
  return nextProgress;
}

export function startWizard() {
  window.localStorage.setItem(
    WIZARD_PROGRESS_KEY,
    JSON.stringify(defaultProgress)
  );
}

export function completeWizard() {
  saveWizardProgress({ currentStep: 4, completed: true });
}

export function wizardStepPath(step: WizardStep) {
  return `/wizard/step-${step}`;
}
