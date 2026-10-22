import {
  registerPdf,
  type TaskSnapshot,
  type UploadDeps,
  type UploadStage
} from "@/lib/documents/upload";
import type { WizardSkillDraft } from "@/lib/wizard/progress";

// El CV que usan el ATS y el match es el principal del casillero 1: subir otro lo reemplaza.
export const PRIMARY_CV_SLOT = 1;

// Lo que deja la lectura de un CV (resultado de la tarea de parseo).
export type CvParseResult = {
  skills?: Array<{
    name: string;
    category?: string | null;
    level?: string | null;
  }>;
};

export type CvStage = UploadStage | "reading";

export type UploadedCv = {
  documentId?: string;
  taskId: string;
  filename: string;
  // La fecha que guardó la API; null si no la devolvió.
  uploadedAt: string | null;
  // Cómo estaba la lectura cuando se cerró el seguimiento: «done» si terminó.
  status: string;
  result: CvParseResult | null;
};

export type CvUploadHandlers = {
  onStage?: (stage: CvStage) => void;
  // El documento ya está registrado y falta leerlo.
  onRegistered?: (registered: { documentId?: string; taskId: string }) => void;
  onTaskUpdate?: (task: TaskSnapshot) => void;
};

/**
 * Sube un CV como principal y espera a que se lea. Es lo que hace el paso 2 del asistente
 * y la tarjeta «Tu CV» de «Mi perfil».
 *
 * La API borra el CV del casillero 1 al registrar el nuevo (después de comprobar el tope
 * diario, así que un pedido bloqueado no borra nada). Por eso, si la lectura falla, el CV
 * anterior ya no está: quien llama lo avisa. Si el seguimiento termina antes de «done» no
 * es un error: el CV quedó registrado y sigue leyéndose.
 */
export async function uploadPrimaryCv(
  file: File,
  profileId: string,
  deps: UploadDeps,
  handlers: CvUploadHandlers = {}
): Promise<UploadedCv> {
  const { document, taskId } = await registerPdf(
    file,
    deps,
    {
      profile_id: profileId,
      type: "cv",
      cv_slot: PRIMARY_CV_SLOT,
      is_primary: true
    },
    handlers.onStage
  );

  handlers.onRegistered?.({ documentId: document.id, taskId });
  handlers.onStage?.("reading");
  const outcome = await deps.waitForTask(taskId, handlers.onTaskUpdate);
  if (outcome.status === "failed") {
    throw new Error(outcome.error || "No se pudo procesar el CV.");
  }

  return {
    documentId: document.id,
    taskId,
    filename: document.original_filename ?? file.name,
    uploadedAt: document.created_at ?? null,
    status: outcome.status,
    result: (outcome.result ?? null) as CvParseResult | null
  };
}

export function toSkillDrafts(result: CvParseResult | null): WizardSkillDraft[] {
  return (result?.skills ?? []).map((skill, index) => ({
    id: `${skill.name}-${index}`,
    name: skill.name,
    category: skill.category ?? null,
    level: skill.level ?? null,
    source: "CV",
    confirmed: false,
    rejected: false
  }));
}

/** «21 oct 2026» o «Oct 21, 2026»; vacío si el valor no es una fecha. */
export function formatCvDate(value: string, language: "es" | "en"): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat(language === "es" ? "es-AR" : "en-US", {
    dateStyle: "medium"
  }).format(date);
}
