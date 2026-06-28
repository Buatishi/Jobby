"use client";

import { useCallback, useState } from "react";
import { AlertCircle, ClipboardPaste, Link2, Send } from "lucide-react";

import { TaskPoller } from "@/components/task-poller";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type JobInputMode = "url" | "text";

type AnalyzeResponse = {
  job_id: string;
  task_id: string;
};

type ToastState = {
  kind: "info" | "success" | "error";
  message: string;
};

export function JobInputForm() {
  const [mode, setMode] = useState<JobInputMode>("url");
  const [url, setUrl] = useState("");
  const [rawText, setRawText] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const showToast = useCallback((nextToast: ToastState) => {
    setToast(nextToast);
  }, []);

  const handleComplete = useCallback(() => {
    showToast({
      kind: "success",
      message: "Análisis completo. Ya podés revisar el job."
    });
    setTaskId(null);
  }, [showToast]);

  const handleFail = useCallback(
    (message: string) => {
      showToast({
        kind: "error",
        message:
          mode === "url"
            ? "No pudimos leer esa URL. Pegá el texto del puesto para continuar."
            : message
      });
      setTaskId(null);
      if (mode === "url") {
        setMode("text");
      }
    },
    [mode, showToast]
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setToast(null);

    try {
      const response = await apiClient<AnalyzeResponse>("/api/v1/jobs/analyze", {
        method: "POST",
        body: JSON.stringify(
          mode === "url"
            ? { source: "url", url }
            : { source: "text", raw_text: rawText }
        )
      });

      setTaskId(response.task_id);
      showToast({
        kind: "info",
        message: "Analizando... te avisamos cuando esté listo."
      });
    } catch (error) {
      showToast({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "No se pudo iniciar el análisis."
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="inline-grid grid-cols-2 rounded-md border border-border bg-muted p-1">
          <button
            className={cn(
              "inline-flex h-9 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium",
              mode === "url" && "bg-background shadow-sm"
            )}
            onClick={() => setMode("url")}
            type="button"
          >
            <Link2 className="h-4 w-4" />
            URL del puesto
          </button>
          <button
            className={cn(
              "inline-flex h-9 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium",
              mode === "text" && "bg-background shadow-sm"
            )}
            onClick={() => setMode("text")}
            type="button"
          >
            <ClipboardPaste className="h-4 w-4" />
            Pegar texto
          </button>
        </div>

        {mode === "url" ? (
          <div className="space-y-3">
            <div className="relative">
              <Link2 className="pointer-events-none absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
              <input
                className="h-12 w-full rounded-md border border-input bg-background pl-11 pr-3 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://empresa.com/jobs/backend-engineer"
                required
                type="url"
                value={url}
              />
            </div>
            <div className="flex gap-2 rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              Algunos sitios bloquean scraping automático. Si falla, vas a poder
              pegar el texto manualmente.
            </div>
          </div>
        ) : (
          <textarea
            className="min-h-36 w-full resize-none rounded-md border border-input bg-background p-3 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
            onChange={(event) => setRawText(event.target.value)}
            placeholder="Pegá acá la descripción completa del puesto"
            required
            value={rawText}
          />
        )}

        <Button className="h-12" disabled={isSubmitting} type="submit">
          <Send className="mr-2 h-4 w-4" />
          {isSubmitting ? "Encolando..." : "Analizar job"}
        </Button>
      </form>

      {toast ? (
        <div
          className={cn(
            "rounded-md border p-4 text-sm",
            toast.kind === "info" && "border-primary/30 bg-primary/5",
            toast.kind === "success" && "border-secondary/30 bg-secondary/5",
            toast.kind === "error" && "border-destructive/30 bg-destructive/5"
          )}
          role="status"
        >
          {toast.message}
        </div>
      ) : null}

      <TaskPoller
        onComplete={handleComplete}
        onFail={handleFail}
        taskId={taskId}
      />
    </div>
  );
}
