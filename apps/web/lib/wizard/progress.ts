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

export type WizardStepOneDraft = {
  // Perfil al que pertenece el borrador: la clave del navegador es una sola para todas las
  // cuentas y sin esto un borrador de otra cuenta aparecería en esta.
  profileId?: string;
  headline?: string;
  summary?: string;
  targetRole?: string;
  targetSeniority?: string;
  workModality?: string;
};

export type WizardProgress = {
  currentStep: WizardStep;
  completed: boolean;
  stepOneDraft?: WizardStepOneDraft;
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

/**
 * Borra el avance guardado en el navegador. La clave es una sola para todas las cuentas y
 * trae datos de la persona (habilidades leídas de su CV): al salir se descarta para que
 * quien entre después en el mismo navegador no lo vea.
 */
export function clearWizardProgress() {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.removeItem(WIZARD_PROGRESS_KEY);
  } catch {
    // Con el almacenamiento bloqueado tampoco se pudo guardar nada que borrar.
  }
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
