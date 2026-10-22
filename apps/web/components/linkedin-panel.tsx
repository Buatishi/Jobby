"use client";

import { useEffect, useRef, useState } from "react";
import { Info } from "lucide-react";

import { PdfPicker } from "@/components/pdf-picker";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { fetchAndRemember, useApiResource } from "@/lib/api/use-api-resource";
import { browserUploadDeps } from "@/lib/documents/browser-deps";
import { useI18n } from "@/lib/i18n/provider";
import {
  describeLinkedInDocument,
  parseLinkedInProfileUrl,
  uploadLinkedInPdf,
  type LinkedInStatus
} from "@/lib/linkedin/linkedin";

const STATUS_PATH = "/api/v1/profiles/linkedin";
const INPUT_CLASS =
  "h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** La URL del perfil de LinkedIn y el PDF que se exporta de ahí, en «Mi perfil». */
export function LinkedInPanel({
  onProfileChange
}: {
  // Se llama cuando cambia algo que mueve el porcentaje del perfil.
  onProfileChange?: () => void;
}) {
  const { t } = useI18n();
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
      await uploadLinkedInPdf(file, status.profile_id, browserUploadDeps);
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
          <p className="text-sm font-medium">{t("app.linkedinPdfLabel")}</p>
          <div className="flex gap-2 rounded-2xl border border-border bg-muted/30 p-3 text-sm">
            <Info className="mt-0.5 h-4 w-4 flex-none text-muted-foreground" />
            <p className="font-medium">{t("app.linkedinPdfNotCv")}</p>
          </div>
          <p className="text-sm text-muted-foreground">{t("app.linkedinPdfHowTo")}</p>
          <PdfPicker
            busy={isUploading}
            busyLabel="Procesando..."
            file={file}
            onFileChange={setFile}
            onUpload={handleUpload}
            pickLabel="Seleccionar PDF"
            uploadDisabled={!status}
            uploadLabel="Subir PDF"
          />
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
