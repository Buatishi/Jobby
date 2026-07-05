"use client";

import { useCallback, useState } from "react";
import { AlertCircle, ClipboardPaste, Link2, Send } from "lucide-react";

import { TaskPoller } from "@/components/task-poller";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

type JobInputMode = "url" | "text";

type AnalyzeResponse = {
  job_id: string;
  task_id: string;
  profile_confidence: "high" | "medium";
};

type ToastState = {
  kind: "info" | "success" | "error";
  message: string;
};

export function JobInputForm() {
  const { t } = useI18n();
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
      message: t("app.analysisComplete")
    });
    setTaskId(null);
  }, [showToast, t]);

  const handleFail = useCallback(
    (message: string) => {
      showToast({
        kind: "error",
        message: mode === "url" ? t("app.urlReadFail") : message
      });
      setTaskId(null);
      if (mode === "url") {
        setMode("text");
      }
    },
    [mode, showToast, t]
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
      window.localStorage.setItem(
        `jobmatch_profile_confidence:${response.job_id}`,
        response.profile_confidence
      );
      showToast({
        kind: "info",
        message: t("app.analysisQueued")
      });
    } catch (error) {
      showToast({
        kind: "error",
        message:
          error instanceof Error ? error.message : t("app.analysisStartFail")
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="inline-grid grid-cols-2 rounded-2xl border border-neutral-100 bg-neutral-50 p-1">
          <button
            className={cn(
              "inline-flex h-10 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold text-black/70 transition",
              mode === "url" && "bg-white text-black shadow-sm"
            )}
            onClick={() => setMode("url")}
            type="button"
          >
            <Link2 className="h-4 w-4" />
            {t("app.jobUrl")}
          </button>
          <button
            className={cn(
              "inline-flex h-10 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold text-black/70 transition",
              mode === "text" && "bg-white text-black shadow-sm"
            )}
            onClick={() => setMode("text")}
            type="button"
          >
            <ClipboardPaste className="h-4 w-4" />
            {t("app.pasteText")}
          </button>
        </div>

        {mode === "url" ? (
          <div className="space-y-3">
            <div className="relative">
              <Link2 className="pointer-events-none absolute left-4 top-3.5 h-5 w-5 text-black/45" />
              <input
                className="h-12 w-full rounded-2xl border border-neutral-100 bg-white pl-12 pr-4 text-sm font-medium outline-none ring-offset-background placeholder:text-black/40 focus-visible:ring-2 focus-visible:ring-[#007a5e]"
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://empresa.com/jobs/backend-engineer"
                required
                type="url"
                value={url}
              />
            </div>
            <div className="flex gap-2 rounded-2xl border border-neutral-100 bg-neutral-50 p-3 text-sm font-medium text-black/60">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#007a5e]" />
              {t("app.scrapingWarning")}
            </div>
          </div>
        ) : (
          <textarea
            className="min-h-36 w-full resize-none rounded-2xl border border-neutral-100 bg-white p-4 text-sm font-medium outline-none ring-offset-background placeholder:text-black/40 focus-visible:ring-2 focus-visible:ring-[#007a5e]"
            onChange={(event) => setRawText(event.target.value)}
            placeholder={t("app.pasteJobDescription")}
            required
            value={rawText}
          />
        )}

        <Button
          className="h-12 rounded-2xl bg-[#007a5e] px-5 font-bold text-white shadow-sm hover:bg-[#006d52]"
          disabled={isSubmitting}
          type="submit"
        >
          <Send className="mr-2 h-4 w-4" />
          {isSubmitting ? t("app.enqueueing") : t("app.analyzeJob")}
        </Button>
      </form>

      {toast ? (
        <div
          className={cn(
            "rounded-2xl border p-4 text-sm font-medium",
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
