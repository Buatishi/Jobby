"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, RotateCcw, ShieldCheck } from "lucide-react";

import { WizardProgress } from "@/components/wizard-progress";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient, apiStream } from "@/lib/api/client";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { saveWizardProgress, type WizardSkillDraft } from "@/lib/wizard/progress";

type ProfileResponse = {
  id: string;
};

type DocumentResponse = {
  id: string;
  task_id?: string;
};

type ParseResult = {
  skills?: Array<{
    name: string;
    category?: string | null;
    level?: string | null;
  }>;
};

type TaskResponse = {
  task_id: string;
  status: "pending" | "processing" | "done" | "failed";
  result: ParseResult | null;
  error: string | null;
};

const maxPdfSize = 10 * 1024 * 1024;

function toSkillDrafts(result: ParseResult | null): WizardSkillDraft[] {
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

export default function WizardStepTwoPage() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState("Elegí un PDF para comenzar.");
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function waitForParsing(nextTaskId: string) {
    await apiStream(`/api/v1/tasks/${nextTaskId}/stream`, (message) => {
      const task = JSON.parse(message) as TaskResponse;
      setStatus(
        task.status === "done"
          ? "CV procesado correctamente."
          : `Procesando CV: ${task.status}`
      );

      if (task.status === "done") {
        saveWizardProgress({
          currentStep: 3,
          taskId: nextTaskId,
          parsedSkills: toSkillDrafts(task.result)
        });
        router.push("/wizard/step-3");
      }

      if (task.status === "failed") {
        setError(task.error ?? "No se pudo procesar el CV.");
      }
    });
  }

  async function handleUpload() {
    if (!selectedFile) {
      setError("Seleccioná un PDF antes de continuar.");
      return;
    }

    if (selectedFile.type !== "application/pdf") {
      setError("El archivo debe ser PDF.");
      return;
    }

    if (selectedFile.size > maxPdfSize) {
      setError("El PDF no puede superar 10MB.");
      return;
    }

    setError(null);
    setIsUploading(true);
    setStatus("Subiendo CV a Supabase Storage...");

    try {
      const supabase = createSupabaseBrowserClient();
      const {
        data: { session }
      } = await supabase.auth.getSession();

      if (!session) {
        throw new Error("Sesión no disponible.");
      }

      const profile = await apiClient<ProfileResponse>("/api/v1/profiles/me");
      const bucket = process.env.NEXT_PUBLIC_SUPABASE_CV_BUCKET ?? "cv-documents";
      const storagePath = `${session.user.id}/${crypto.randomUUID()}-${selectedFile.name}`;
      const { error: uploadError } = await supabase.storage
        .from(bucket)
        .upload(storagePath, selectedFile, {
          contentType: "application/pdf",
          upsert: false
        });

      if (uploadError) {
        throw uploadError;
      }

      setStatus("Registrando documento y encolando parsing...");
      const document = await apiClient<DocumentResponse>(
        "/api/v1/profiles/documents",
        {
          method: "POST",
          body: JSON.stringify({
            profile_id: profile.id,
            type: "cv",
            cv_slot: 1,
            is_primary: true,
            storage_path: storagePath,
            original_filename: selectedFile.name,
            mime_type: selectedFile.type,
            file_size: selectedFile.size
          })
        }
      );

      if (!document.task_id) {
        throw new Error("El backend no devolvió el task de parsing.");
      }

      setTaskId(document.task_id);
      saveWizardProgress({
        currentStep: 2,
        documentId: document.id,
        taskId: document.task_id
      });
      setStatus("Esperando resultado del parser...");
      await waitForParsing(document.task_id);
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
          <div className="rounded-md border border-[#0F6E56]/20 bg-[#0F6E56]/5 p-4 text-sm">
            <div className="flex gap-3">
              <ShieldCheck className="mt-0.5 h-4 w-4 flex-none text-[#0F6E56]" />
              <p className="text-muted-foreground">
                El CV ayuda a que Jobby detecte evidencia real. Si todavía no
                lo tenés listo, podés avanzar y cargarlo después desde tu perfil.
              </p>
            </div>
          </div>

          <label className="flex min-h-52 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/30 p-6 text-center">
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

          <div className="rounded-md border border-border p-4 text-sm">
            <p className="font-medium">{status}</p>
            {taskId ? (
              <p className="mt-1 text-muted-foreground">Task: {taskId}</p>
            ) : null}
          </div>

          {error ? (
            <div className="rounded-md border border-destructive/40 p-4 text-sm text-destructive">
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
                saveWizardProgress({ currentStep: 3 });
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
