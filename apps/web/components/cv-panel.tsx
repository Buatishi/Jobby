"use client";

import { useState } from "react";

import { PdfPicker } from "@/components/pdf-picker";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import {
  formatCvDate,
  uploadPrimaryCv,
  type CvStage
} from "@/lib/cv/upload";
import { browserUploadDeps, fetchProfileId } from "@/lib/documents/browser-deps";
import { useI18n } from "@/lib/i18n/provider";

// El CV que se subió en esta sesión. La API no tiene cómo devolver el CV principal que
// ya estaba guardado, así que antes de subir uno no hay nada que mostrar.
export type CurrentCv = {
  filename: string;
  uploadedAt: string | null;
};

const STAGE_KEYS: Record<CvStage, string> = {
  uploading: "app.cvStageUploading",
  registering: "app.cvStageRegistering",
  reading: "app.cvStageReading"
};

export type CvPanelViewProps = {
  file: File | null;
  busy: boolean;
  stageText: string | null;
  current: CurrentCv | null;
  notice: string | null;
  error: string | null;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
};

export function CvPanelView({
  file,
  busy,
  stageText,
  current,
  notice,
  error,
  onFileChange,
  onUpload
}: CvPanelViewProps) {
  const { t, language } = useI18n();
  const uploadedOn = current?.uploadedAt ? formatCvDate(current.uploadedAt, language) : "";

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("app.cvCardTitle")}</CardTitle>
        <CardDescription>{t("app.cvCardDescription")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {current ? (
          <p className="text-sm font-medium">
            {uploadedOn
              ? t("app.cvCardCurrent", { name: current.filename, date: uploadedOn })
              : t("app.cvCardCurrentNoDate", { name: current.filename })}
          </p>
        ) : null}

        <PdfPicker
          busy={busy}
          busyLabel={t("app.cvCardProcessing")}
          file={file}
          onFileChange={onFileChange}
          onUpload={onUpload}
          pickLabel={t("app.cvCardPick")}
          uploadLabel={t("app.cvCardUpload")}
        />

        <p className="text-sm text-muted-foreground">{t("app.cvCardReplaceNote")}</p>

        {stageText ? (
          <p className="text-sm text-muted-foreground" role="status">
            {stageText}
          </p>
        ) : null}
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

/**
 * Sube un CV nuevo como principal desde «Mi perfil». Usa la misma subida que el paso 2 del
 * asistente (`uploadPrimaryCv`). Mientras se sube y se lee, el selector y el botón quedan
 * bloqueados: no se puede empezar otra subida desde esta pestaña.
 */
export function CvPanel({
  onProfileChange
}: {
  // Se llama al terminar, salga como salga: el porcentaje del perfil puede haber cambiado.
  onProfileChange?: () => void;
}) {
  const { t } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<CvStage | null>(null);
  const [current, setCurrent] = useState<CurrentCv | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) {
      setError(t("app.cvCardPickFirst"));
      return;
    }

    setError(null);
    setNotice(null);
    setBusy(true);
    setStage("uploading");
    // Desde que el CV queda registrado, el anterior ya no está: si algo falla después,
    // hay que avisarlo. Antes (tope diario, archivo inválido) no se tocó nada.
    let registered = false;
    try {
      const profileId = await fetchProfileId();
      const uploaded = await uploadPrimaryCv(file, profileId, browserUploadDeps, {
        onStage: (next) => {
          setStage(next);
          if (next === "reading") {
            registered = true;
          }
        }
      });
      setFile(null);
      setCurrent({
        filename: uploaded.filename,
        uploadedAt: uploaded.uploadedAt ?? new Date().toISOString()
      });
      setNotice(uploaded.status === "done" ? t("app.cvCardDone") : t("app.cvCardStillReading"));
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : t("app.cvCardUploadError");
      setError(registered ? `${message} ${t("app.cvReadFailedHint")}` : message);
    } finally {
      setBusy(false);
      setStage(null);
      onProfileChange?.();
    }
  }

  return (
    <CvPanelView
      busy={busy}
      current={current}
      error={error}
      file={file}
      notice={notice}
      onFileChange={setFile}
      onUpload={() => void handleUpload()}
      stageText={stage ? t(STAGE_KEYS[stage]) : null}
    />
  );
}
