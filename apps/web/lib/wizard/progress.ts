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
  // Cuenta a la que pertenece el avance: la clave del navegador es una sola para todas
  // las cuentas y sin dueño lo que una persona avanzó (habilidades leídas de su CV) lo
  // vería la siguiente que entre desde el mismo navegador.
  ownerId?: string;
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

// Cuenta que está usando el wizard, o `null` si todavía no se sabe quién es (o no se pudo
// cargar): sin dueño conocido no se lee, no se guarda y no se borra nada de nadie.
type Owner = string | null;

function readStored(): Partial<WizardProgress> | null {
  const rawProgress = window.localStorage.getItem(WIZARD_PROGRESS_KEY);
  if (!rawProgress) {
    return null;
  }

  try {
    const parsed: unknown = JSON.parse(rawProgress);
    return typeof parsed === "object" && parsed !== null
      ? (parsed as Partial<WizardProgress>)
      : null;
  } catch {
    return null;
  }
}

/** El avance guardado si es de esta cuenta; si es de otra (o no tiene dueño) lo descarta. */
function readOwned(ownerId: Owner): Partial<WizardProgress> | null {
  if (typeof window === "undefined" || ownerId === null) {
    return null;
  }

  const stored = readStored();
  if (stored === null) {
    return null;
  }
  if (stored.ownerId !== ownerId) {
    clearWizardProgress();
    return null;
  }
  return stored;
}

export function getWizardProgress(ownerId: Owner): WizardProgress {
  const stored = readOwned(ownerId);
  return stored === null ? defaultProgress : ({ ...defaultProgress, ...stored } as WizardProgress);
}

export function hasWizardProgress(ownerId: Owner) {
  return readOwned(ownerId) !== null;
}

export function saveWizardProgress(ownerId: Owner, update: Partial<WizardProgress>) {
  const nextProgress = { ...getWizardProgress(ownerId), ...update };
  if (ownerId !== null) {
    window.localStorage.setItem(
      WIZARD_PROGRESS_KEY,
      JSON.stringify({ ...nextProgress, ownerId })
    );
  }
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

export function startWizard(ownerId: Owner) {
  saveWizardProgress(ownerId, defaultProgress);
}

export function completeWizard(ownerId: Owner) {
  saveWizardProgress(ownerId, { currentStep: 4, completed: true });
}

export function wizardStepPath(step: WizardStep) {
  return `/wizard/step-${step}`;
}
