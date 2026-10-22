import {
  MAX_PDF_BYTES,
  registerPdf,
  validatePdf,
  type UploadDeps
} from "@/lib/documents/upload";

// Lo que devuelve GET /api/v1/profiles/linkedin.
export type LinkedInDocument = {
  id: string;
  status: string;
  original_filename?: string | null;
  error_msg?: string | null;
  created_at?: string | null;
};

export type LinkedInStatus = {
  profile_id: string;
  linkedin_url?: string | null;
  document?: LinkedInDocument | null;
  // Skills ya guardadas en el perfil que el PDF de LinkedIn nombra.
  skills_in_linkedin?: number;
};

export const MAX_LINKEDIN_PDF_BYTES = MAX_PDF_BYTES;
const MAX_URL_LENGTH = 2048;
const MIN_USERNAME_LENGTH = 3;

export type LinkedInUrlResult =
  | { ok: true; value: string | null }
  | { ok: false; error: string };

export const LINKEDIN_URL_ERROR =
  "Pegá el enlace de tu perfil, por ejemplo https://www.linkedin.com/in/tu-usuario.";

/**
 * Mismo criterio que usa la API para dar los puntos (`is_linkedin_profile_url`):
 * `linkedin.com/in/<usuario>` con usuario real. Vacío es válido y borra el enlace.
 * Se guarda con `https://` aunque la persona lo haya pegado sin él.
 */
export function parseLinkedInProfileUrl(input: string): LinkedInUrlResult {
  const trimmed = input.trim();
  if (trimmed === "") {
    return { ok: true, value: null };
  }

  const candidate = trimmed.includes("://") ? trimmed : `https://${trimmed}`;
  if (candidate.length > MAX_URL_LENGTH) {
    return { ok: false, error: LINKEDIN_URL_ERROR };
  }

  let url: URL;
  try {
    url = new URL(candidate);
  } catch {
    return { ok: false, error: LINKEDIN_URL_ERROR };
  }

  const host = url.hostname.toLowerCase();
  const isLinkedIn = host === "linkedin.com" || host.endsWith(".linkedin.com");
  const parts = url.pathname.split("/").filter(Boolean);
  const isProfile =
    parts.length >= 2 &&
    parts[0]?.toLowerCase() === "in" &&
    (parts[1]?.length ?? 0) >= MIN_USERNAME_LENGTH;

  if (!["http:", "https:"].includes(url.protocol) || !isLinkedIn || !isProfile) {
    return { ok: false, error: LINKEDIN_URL_ERROR };
  }
  return { ok: true, value: candidate };
}

export const validateLinkedInPdf = validatePdf;

export type LinkedInDocumentSummary = {
  tone: "empty" | "working" | "done" | "failed";
  text: string;
};

export function describeLinkedInDocument(
  status: LinkedInStatus | undefined
): LinkedInDocumentSummary {
  const document = status?.document;
  if (!document) {
    return { tone: "empty", text: "Todavía no subiste tu PDF de LinkedIn." };
  }

  if (document.status === "pending" || document.status === "processing") {
    return { tone: "working", text: "Estamos leyendo tu PDF de LinkedIn…" };
  }

  if (document.status === "failed") {
    return {
      tone: "failed",
      text: document.error_msg || "No pudimos leer el PDF. Probá subirlo de nuevo."
    };
  }

  const found = status?.skills_in_linkedin ?? 0;
  return {
    tone: "done",
    text:
      found > 0
        ? `Leído: ${found} de tus skills figuran en tu LinkedIn.`
        : "Lo leímos, pero ninguna skill de las que ya cargaste figura en él. Confirmá tus skills y volvé a subirlo."
  };
}

export type LinkedInUploadDeps = UploadDeps;

/**
 * Sube el PDF de LinkedIn y espera a que se lea. Falla con un mensaje legible; si el
 * documento quedó registrado, la tarjeta vuelve a pedir el estado y lo muestra.
 */
export async function uploadLinkedInPdf(
  file: File,
  profileId: string,
  deps: LinkedInUploadDeps
): Promise<void> {
  const { taskId } = await registerPdf(file, deps, {
    profile_id: profileId,
    type: "linkedin",
    is_primary: false
  });

  const outcome = await deps.waitForTask(taskId);
  if (outcome.status === "failed") {
    throw new Error(outcome.error || "No se pudo leer el PDF de LinkedIn.");
  }
}
