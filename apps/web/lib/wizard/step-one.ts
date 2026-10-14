import type { WizardStepOneDraft } from "@/lib/wizard/progress";

export const SENIORITY_OPTIONS = [
  "junior",
  "mid",
  "senior",
  "staff",
  "principal"
] as const;

export const WORK_MODALITIES = [
  { value: "remote", label: "Remoto" },
  { value: "hybrid", label: "Híbrido" },
  { value: "onsite", label: "Presencial" }
] as const;

export type StepOneValues = {
  headline: string;
  summary: string;
  targetRole: string;
  targetSeniority: string;
  workModality: string;
};

// Lo que devuelve GET /api/v1/profiles/me y que usa este paso.
export type StepOneProfile = {
  id?: string | null;
  headline?: string | null;
  summary?: string | null;
  target_role?: string | null;
  target_seniority?: string | null;
  work_modality?: string | null;
};

export type StepOneResolution = {
  values: StepOneValues;
  // Verdadero si algún campo vino de lo que la persona ya tenía guardado.
  prefilled: boolean;
};

const DEFAULTS: StepOneValues = {
  headline: "",
  summary: "",
  targetRole: "",
  targetSeniority: "mid",
  workModality: "remote"
};

const SENIORITIES: readonly string[] = SENIORITY_OPTIONS;
const MODALITIES: readonly string[] = WORK_MODALITIES.map((option) => option.value);

function filled(value: string | null | undefined): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

function oneOf(
  value: string | null | undefined,
  allowed: readonly string[]
): string | null {
  const normalized = filled(value)?.trim().toLowerCase();
  return normalized && allowed.includes(normalized) ? normalized : null;
}

/**
 * Valores con los que abre el paso 1.
 *
 * Gana lo que ya está guardado en el perfil: quien toca «Mejorar perfil» ve su perfil y
 * edita solo lo que quiere cambiar. El borrador del navegador solo completa lo que falta
 * y únicamente si es de este mismo perfil: se guarda en una clave única del navegador, y
 * si lo leyera otra cuenta le mostraría (y le guardaría) datos ajenos.
 */
export function resolveStepOneValues(
  profile: StepOneProfile | null,
  draft: WizardStepOneDraft | undefined
): StepOneResolution {
  // Sin perfil (falló la carga) se usa el borrador como antes; con perfil, solo el suyo.
  const usableDraft =
    draft && (profile === null || (profile.id && draft.profileId === profile.id))
      ? draft
      : undefined;

  const fromProfile = {
    headline: filled(profile?.headline),
    summary: filled(profile?.summary),
    targetRole: filled(profile?.target_role),
    targetSeniority: oneOf(profile?.target_seniority, SENIORITIES),
    workModality: oneOf(profile?.work_modality, MODALITIES)
  };

  const values: StepOneValues = {
    headline: fromProfile.headline ?? filled(usableDraft?.headline) ?? DEFAULTS.headline,
    summary: fromProfile.summary ?? filled(usableDraft?.summary) ?? DEFAULTS.summary,
    targetRole:
      fromProfile.targetRole ?? filled(usableDraft?.targetRole) ?? DEFAULTS.targetRole,
    targetSeniority:
      fromProfile.targetSeniority ??
      oneOf(usableDraft?.targetSeniority, SENIORITIES) ??
      DEFAULTS.targetSeniority,
    workModality:
      fromProfile.workModality ??
      oneOf(usableDraft?.workModality, MODALITIES) ??
      DEFAULTS.workModality
  };

  return {
    values,
    prefilled: Object.values(fromProfile).some((value) => value !== null)
  };
}
