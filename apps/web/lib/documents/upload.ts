// Lo que comparten las subidas de un PDF a «Mi perfil» y al asistente (el CV y el PDF de
// LinkedIn): validar el archivo, guardarlo en la carpeta de la persona y registrarlo en la API.

export const MAX_PDF_BYTES = 10 * 1024 * 1024;

export function validatePdf(file: { type: string; size: number }): string | null {
  if (file.type !== "application/pdf") {
    return "El archivo debe ser un PDF.";
  }
  if (file.size === 0) {
    return "El PDF está vacío.";
  }
  if (file.size > MAX_PDF_BYTES) {
    return "El PDF no puede superar 10MB.";
  }
  return null;
}

// Un mensaje de la tarea de lectura (GET /api/v1/tasks/{id}/stream).
export type TaskSnapshot = {
  status: string;
  error?: string | null;
  result?: unknown;
};

// Lo que devuelve POST /api/v1/profiles/documents.
export type RegisteredDocument = {
  id?: string;
  task_id?: string | null;
  original_filename?: string | null;
  created_at?: string | null;
};

export type UploadDeps = {
  // Id de la persona en Supabase Auth: la carpeta donde puede guardar archivos.
  userId: () => Promise<string>;
  uploadFile: (storagePath: string, file: File) => Promise<void>;
  registerDocument: (body: Record<string, unknown>) => Promise<RegisteredDocument>;
  // Espera a que termine la lectura y devuelve cómo terminó; `onUpdate` ve cada avance.
  waitForTask: (
    taskId: string,
    onUpdate?: (task: TaskSnapshot) => void
  ) => Promise<TaskSnapshot>;
  newId: () => string;
};

export type UploadStage = "uploading" | "registering";

/**
 * Valida el PDF, lo guarda en la carpeta de la persona y lo registra con los campos que
 * pida cada tipo de documento. Falla con un mensaje legible; no espera la lectura.
 */
export async function registerPdf(
  file: File,
  deps: UploadDeps,
  fields: Record<string, unknown>,
  onStage?: (stage: UploadStage) => void
): Promise<{ document: RegisteredDocument; taskId: string }> {
  const invalid = validatePdf(file);
  if (invalid) {
    throw new Error(invalid);
  }

  onStage?.("uploading");
  const userId = await deps.userId();
  const storagePath = `${userId}/${deps.newId()}-${file.name}`;
  await deps.uploadFile(storagePath, file);

  onStage?.("registering");
  const document = await deps.registerDocument({
    ...fields,
    storage_path: storagePath,
    original_filename: file.name,
    mime_type: file.type,
    file_size: file.size
  });
  if (!document.task_id) {
    throw new Error("El servidor no devolvió la tarea de lectura.");
  }

  return { document, taskId: document.task_id };
}
