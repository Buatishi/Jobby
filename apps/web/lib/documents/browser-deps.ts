import { apiClient, apiStream } from "@/lib/api/client";
import type {
  RegisteredDocument,
  TaskSnapshot,
  UploadDeps
} from "@/lib/documents/upload";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

// Las dependencias reales de la subida de un PDF, para el navegador: Storage de Supabase
// para el archivo y la API de Jobby para registrarlo y seguir su lectura. Las usan el
// asistente y las tarjetas de «Mi perfil»; los tests pasan las suyas.
export const browserUploadDeps: UploadDeps = {
  userId: async () => {
    const {
      data: { session }
    } = await createSupabaseBrowserClient().auth.getSession();
    if (!session) {
      throw new Error("Sesión no disponible.");
    }
    return session.user.id;
  },
  uploadFile: async (storagePath, file) => {
    const bucket = process.env.NEXT_PUBLIC_SUPABASE_CV_BUCKET ?? "cv-documents";
    const { error } = await createSupabaseBrowserClient()
      .storage.from(bucket)
      .upload(storagePath, file, { contentType: "application/pdf", upsert: false });
    if (error) {
      throw error;
    }
  },
  registerDocument: (body) =>
    apiClient<RegisteredDocument>("/api/v1/profiles/documents", {
      method: "POST",
      body: JSON.stringify(body)
    }),
  waitForTask: async (taskId, onUpdate) => {
    let outcome: TaskSnapshot = { status: "pending" };
    await apiStream(`/api/v1/tasks/${taskId}/stream`, (message) => {
      try {
        outcome = JSON.parse(message) as TaskSnapshot;
      } catch {
        // Un mensaje que no es JSON no cambia cómo terminó la tarea.
        return;
      }
      onUpdate?.(outcome);
    });
    return outcome;
  },
  newId: () => crypto.randomUUID()
};

/** El id del perfil de quien está en sesión: el documento se registra a su nombre. */
export async function fetchProfileId(): Promise<string> {
  const profile = await apiClient<{ id: string }>("/api/v1/profiles/me");
  return profile.id;
}
