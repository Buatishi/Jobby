"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, RotateCcw, ShieldCheck } from "lucide-react";

import { WizardProgress } from "@/components/wizard-progress";
import { useWizardOwner } from "@/components/wizard-owner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { toSkillDrafts, uploadPrimaryCv, type CvStage } from "@/lib/cv/upload";
import { browserUploadDeps, fetchProfileId } from "@/lib/documents/browser-deps";
import { validatePdf } from "@/lib/documents/upload";
import { saveWizardProgress } from "@/lib/wizard/progress";

const STAGE_STATUS: Record<CvStage, string> = {
  uploading: "Subiendo CV a Supabase Storage...",
  registering: "Registrando documento y encolando parsing...",
  reading: "Esperando resultado del parser..."
};

export default function WizardStepTwoPage() {
  const router = useRouter();
  const ownerId = useWizardOwner();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState("Elegí un PDF para comenzar.");
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleUpload() {
    if (!selectedFile) {
      setError("Seleccioná un PDF antes de continuar.");
      return;
    }

    const invalid = validatePdf(selectedFile);
    if (invalid) {
      setError(invalid);
      return;
    }

    setError(null);
    setIsUploading(true);
    setStatus(STAGE_STATUS.uploading);

    try {
      // La misma subida que usa la tarjeta «Tu CV» de «Mi perfil»: valida el PDF, lo guarda,
      // lo registra como CV principal (casillero 1) y espera a que se lea.
      const profileId = await fetchProfileId();
      const uploaded = await uploadPrimaryCv(selectedFile, profileId, browserUploadDeps, {
        onStage: (stage) => setStatus(STAGE_STATUS[stage]),
        onRegistered: ({ documentId, taskId: nextTaskId }) => {
          setTaskId(nextTaskId);
          saveWizardProgress(ownerId, { currentStep: 2, documentId, taskId: nextTaskId });
        },
        onTaskUpdate: (task) =>
          setStatus(
            task.status === "done"
              ? "CV procesado correctamente."
              : `Procesando CV: ${task.status}`
          )
      });

      if (uploaded.status === "done") {
        saveWizardProgress(ownerId, {
          currentStep: 3,
          taskId: uploaded.taskId,
          parsedSkills: toSkillDrafts(uploaded.result)
        });
        router.push("/wizard/step-3");
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo subir el CV."
      );
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <WizardProgress currentStep={2} completionPercent={35} />
      <Card>
        <CardHeader>
          <CardTitle>Subí tu CV</CardTitle>
          <CardDescription>
            Usamos el PDF para extraer skills, experiencia y educación inicial.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="rounded-2xl border border-brand-green/20 bg-brand-green-light p-4 text-sm">
            <div className="flex gap-3">
              <ShieldCheck className="mt-0.5 h-4 w-4 flex-none text-brand-green" />
              <p className="text-muted-foreground">
                El CV ayuda a que Jobby detecte evidencia real. Si todavía no
                lo tenés listo, podés avanzar y cargarlo después desde tu perfil.
              </p>
            </div>
          </div>

          <label className="flex min-h-52 cursor-pointer flex-col items-center justify-center rounded-card border border-dashed border-border bg-muted/30 p-6 text-center">
            <FileUp className="h-10 w-10 text-muted-foreground" />
            <span className="mt-3 font-medium">
              {selectedFile ? selectedFile.name : "Seleccionar PDF"}
            </span>
            <span className="mt-1 text-sm text-muted-foreground">
              Máximo 10MB
            </span>
            <input
              accept="application/pdf"
              className="sr-only"
              disabled={isUploading}
              onChange={(event) =>
                setSelectedFile(event.target.files?.item(0) ?? null)
              }
              type="file"
            />
          </label>

          <div className="rounded-2xl border border-border p-4 text-sm">
            <p className="font-medium">{status}</p>
            {taskId ? (
              <p className="mt-1 text-muted-foreground">Task: {taskId}</p>
            ) : null}
          </div>

          {error ? (
            <div className="rounded-2xl border border-destructive/40 p-4 text-sm text-destructive">
              <p>{error}</p>
              <Button
                className="mt-3"
                disabled={isUploading}
                onClick={handleUpload}
                type="button"
                variant="secondary"
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Reintentar
              </Button>
            </div>
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row">
            <Button disabled={isUploading} onClick={handleUpload} type="button">
              {isUploading ? "Procesando..." : "Subir y analizar CV"}
            </Button>
            <Button
              disabled={isUploading}
              onClick={() => {
                saveWizardProgress(ownerId, { currentStep: 3 });
                router.push("/wizard/step-3");
              }}
              type="button"
              variant="ghost"
            >
              Cargar CV más tarde
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
