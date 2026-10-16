"use client";

import { useEffect, useRef, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient, apiStream } from "@/lib/api/client";
import { fetchAndRemember, useApiResource } from "@/lib/api/use-api-resource";
import {
  describeLinkedInDocument,
  parseLinkedInProfileUrl,
  uploadLinkedInPdf,
  type LinkedInStatus,
  type LinkedInUploadDeps
} from "@/lib/linkedin/linkedin";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const STATUS_PATH = "/api/v1/profiles/linkedin";
const INPUT_CLASS =
  "h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

const uploadDeps: LinkedInUploadDeps = {
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
    apiClient<{ task_id?: string | null }>("/api/v1/profiles/documents", {
      method: "POST",
      body: JSON.stringify(body)
    }),
  waitForTask: async (taskId) => {
    let outcome: { status: string; error?: string | null } = { status: "pending" };
    await apiStream(`/api/v1/tasks/${taskId}/stream`, (message) => {
      try {
        outcome = JSON.parse(message) as typeof outcome;
      } catch {
        // Un mensaje que no es JSON no cambia cómo terminó la tarea.
      }
    });
    return outcome;
  },
  newId: () => crypto.randomUUID()
};

/** La URL del perfil de LinkedIn y el PDF que se exporta de ahí, en «Mi perfil». */
export function LinkedInPanel({
  onProfileChange
}: {
  // Se llama cuando cambia algo que mueve el porcentaje del perfil.
  onProfileChange?: () => void;
}) {
  const {
    data: status,
    error: loadError,
    mutate
  } = useApiResource<LinkedInStatus>(STATUS_PATH, "No se pudo cargar tu LinkedIn.");
  const [url, setUrl] = useState("");
  const urlTouched = useRef(false);
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSavingUrl, setIsSavingUrl] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    // El enlace guardado llena el campo, salvo que la persona ya haya escrito.
    if (status && !urlTouched.current) {
      setUrl(status.linkedin_url ?? "");
    }
  }, [status]);

  async function refresh() {
    const fresh = await fetchAndRemember<LinkedInStatus>(STATUS_PATH);
    mutate(() => fresh);
    onProfileChange?.();
  }

  async function handleSaveUrl(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    const parsed = parseLinkedInProfileUrl(url);
    if (!parsed.ok) {
      setError(parsed.error);
      return;
    }

    setIsSavingUrl(true);
    try {
      await apiClient("/api/v1/profiles/me", {
        method: "PATCH",
        // Valor absoluto: repetirlo deja lo mismo (un deploy puede dar 502).
        idempotent: true,
        body: JSON.stringify({ linkedin_url: parsed.value })
      });
      urlTouched.current = false;
      setNotice(parsed.value ? "Enlace guardado." : "Enlace quitado.");
      await refresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo guardar el enlace."
      );
    } finally {
      setIsSavingUrl(false);
    }
  }

  async function handleUpload() {
    if (!file || !status) {
      setError("Elegí el PDF de tu perfil antes de subirlo.");
      return;
    }

    setError(null);
    setNotice(null);
    setIsUploading(true);
    try {
      await uploadLinkedInPdf(file, status.profile_id, uploadDeps);
      setFile(null);
      setNotice("PDF de LinkedIn procesado.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo subir el PDF."
      );
    } finally {
      try {
        // Haya salido bien o no, el documento puede haber quedado registrado.
        await refresh();
      } catch {
        // Si el estado no llega, queda el último que se mostró.
      }
      setIsUploading(false);
    }
  }

  const summary = describeLinkedInDocument(status);

  return (
    <Card>
      <CardHeader>
        <CardTitle>LinkedIn</CardTitle>
        <CardDescription>
          Sumá tu perfil de LinkedIn para comparar lo que decís en el CV con lo que
          mostrás ahí. Suma al porcentaje de tu perfil.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {loadError ? <p className="text-sm text-destructive">{loadError}</p> : null}

        <form className="space-y-2" onSubmit={handleSaveUrl}>
          <label className="text-sm font-medium" htmlFor="linkedin-url">
            Enlace a tu perfil
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              className={INPUT_CLASS}
              id="linkedin-url"
              inputMode="url"
              onChange={(event) => {
                urlTouched.current = true;
                setUrl(event.target.value);
              }}
              placeholder="https://www.linkedin.com/in/tu-usuario"
              value={url}
            />
            <Button
              className="sm:flex-none"
              disabled={isSavingUrl || !status}
              type="submit"
            >
              {isSavingUrl ? "Guardando..." : "Guardar enlace"}
            </Button>
          </div>
        </form>

        <div className="space-y-2">
          <p className="text-sm font-medium">PDF de tu perfil</p>
          <p className="text-sm text-muted-foreground">
            En LinkedIn, desde tu perfil, elegí «Recursos» (o «Más») y después «Guardar
            en PDF». Subí ese archivo acá: marcamos cuáles de tus skills figuran en
            LinkedIn. No agregamos skills nuevas a tu perfil.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="flex h-11 min-w-0 flex-1 cursor-pointer items-center gap-3 rounded-full border border-dashed border-border bg-muted/30 px-5 text-sm">
              <FileUp className="h-4 w-4 flex-none text-muted-foreground" />
              <span className="truncate">{file ? file.name : "Seleccionar PDF"}</span>
              <input
                accept="application/pdf"
                className="sr-only"
                disabled={isUploading}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                type="file"
              />
            </label>
            <Button
              className="sm:flex-none"
              disabled={isUploading || !file || !status}
              onClick={handleUpload}
              type="button"
            >
              {isUploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Procesando...
                </>
              ) : (
                "Subir PDF"
              )}
            </Button>
          </div>
          <p
            className={
              summary.tone === "failed"
                ? "text-sm text-destructive"
                : "text-sm text-muted-foreground"
            }
            role="status"
          >
            {summary.text}
          </p>
        </div>

        {notice ? (
          <p className="text-sm text-brand-green" role="status">
            {notice}
          </p>
        ) : null}
        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
