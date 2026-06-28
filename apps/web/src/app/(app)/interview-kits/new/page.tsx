"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";

import { ProgressSteps } from "@/components/progress-steps";
import { TaskPoller } from "@/components/task-poller";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";

type JobHistoryItem = {
  id: string;
  job_title: string | null;
  company_name: string | null;
};

type JobAnalyzeResponse = {
  job_id: string;
  task_id: string;
};

type InterviewKitResponse = {
  id: string;
  task_id?: string | null;
};

const companyLinkedInPattern = /linkedin\.com\/company\//i;
const interviewerLinkedInPattern = /linkedin\.com\/in\//i;

function parseLinkedInName(url: string) {
  const clean = url.replace(/\/$/, "");
  const segment = clean.split("/").filter(Boolean).pop();
  return segment ? segment.replace(/-/g, " ") : "";
}

export default function NewInterviewKitPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobHistoryItem[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [newJobUrl, setNewJobUrl] = useState("");
  const [companyLinkedInUrl, setCompanyLinkedInUrl] = useState("");
  const [interviewerLinkedInUrl, setInterviewerLinkedInUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [jobTaskId, setJobTaskId] = useState<string | null>(null);
  const [kitTaskId, setKitTaskId] = useState<string | null>(null);
  const [pendingJobId, setPendingJobId] = useState<string | null>(null);
  const [createdKitId, setCreatedKitId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    async function loadJobs() {
      try {
        const response = await apiClient<JobHistoryItem[]>("/api/v1/jobs");
        setJobs(response);
      } catch {
        setJobs([]);
      }
    }

    void loadJobs();
  }, []);

  const companyName = useMemo(
    () => parseLinkedInName(companyLinkedInUrl) || "la empresa",
    [companyLinkedInUrl]
  );
  const interviewerName = useMemo(
    () => parseLinkedInName(interviewerLinkedInUrl) || "el entrevistador",
    [interviewerLinkedInUrl]
  );

  const createKit = useCallback(
    async (jobId: string) => {
      setCurrentStep(2);
      const kit = await apiClient<InterviewKitResponse>(
        "/api/v1/interview-kits",
        {
          method: "POST",
          body: JSON.stringify({
            job_id: jobId,
            company_linkedin_url: companyLinkedInUrl,
            interviewer_linkedin_url: interviewerLinkedInUrl,
            interviewer_name: interviewerName,
            interviewer_role: "",
            notes
          })
        }
      );
      setCreatedKitId(kit.id);
      setKitTaskId(kit.task_id ?? null);
      setCurrentStep(4);
      if (!kit.task_id) {
        router.push(`/interview-kits/${kit.id}`);
      }
    },
    [
      companyLinkedInUrl,
      interviewerLinkedInUrl,
      interviewerName,
      notes,
      router
    ]
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFailed(false);

    if (!selectedJobId && !newJobUrl.trim()) {
      setError("Elegí un job del historial o pegá una URL nueva.");
      return;
    }
    if (!companyLinkedInPattern.test(companyLinkedInUrl)) {
      setError("El LinkedIn de la empresa debe incluir linkedin.com/company/.");
      return;
    }
    if (!interviewerLinkedInPattern.test(interviewerLinkedInUrl)) {
      setError("El LinkedIn del entrevistador debe incluir linkedin.com/in/.");
      return;
    }

    setSubmitting(true);
    try {
      if (selectedJobId) {
        await createKit(selectedJobId);
        return;
      }

      setCurrentStep(1);
      const response = await apiClient<JobAnalyzeResponse>("/api/v1/jobs/analyze", {
        method: "POST",
        body: JSON.stringify({
          source: "url",
          url: newJobUrl,
          raw_text: null
        })
      });
      setPendingJobId(response.job_id);
      setJobTaskId(response.task_id);
    } catch (requestError) {
      setFailed(true);
      setSubmitting(false);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo iniciar la generación."
      );
    }
  }

  const handleJobAnalyzed = useCallback(() => {
    if (!pendingJobId) {
      return;
    }
    void createKit(pendingJobId).catch((requestError: unknown) => {
      setFailed(true);
      setSubmitting(false);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo generar el kit."
      );
    });
  }, [createKit, pendingJobId]);

  const handleKitComplete = useCallback(() => {
    if (createdKitId) {
      router.push(`/interview-kits/${createdKitId}`);
    }
  }, [createdKitId, router]);

  const handleTaskFail = useCallback((message: string) => {
    setFailed(true);
    setSubmitting(false);
    setError(message);
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:py-8">
      <div className="mb-6">
        <p className="text-sm font-medium text-muted-foreground">
          Nuevo Interview Kit
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-normal">
          Generá tu preparación personalizada
        </h1>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Datos de la entrevista</CardTitle>
            <CardDescription>
              Usá un puesto ya analizado o pegá una URL nueva para analizarlo
              antes de crear el kit.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={handleSubmit}>
              <label className="block text-sm font-medium">
                Job del historial
                <select
                  className="mt-2 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  onChange={(event) => setSelectedJobId(event.target.value)}
                  value={selectedJobId}
                >
                  <option value="">Usar URL nueva</option>
                  {jobs.map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.job_title ?? "Puesto"} ·{" "}
                      {job.company_name ?? "Empresa"}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-sm font-medium">
                URL nueva del puesto
                <input
                  className="mt-2 h-10 w-full rounded-md border border-input bg-background px-3 text-sm disabled:opacity-50"
                  disabled={Boolean(selectedJobId)}
                  onChange={(event) => setNewJobUrl(event.target.value)}
                  placeholder="https://..."
                  type="url"
                  value={newJobUrl}
                />
              </label>

              <label className="block text-sm font-medium">
                LinkedIn de la empresa
                <input
                  className="mt-2 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  onChange={(event) =>
                    setCompanyLinkedInUrl(event.target.value)
                  }
                  placeholder="https://www.linkedin.com/company/empresa"
                  required
                  type="url"
                  value={companyLinkedInUrl}
                />
              </label>

              <label className="block text-sm font-medium">
                LinkedIn del entrevistador
                <input
                  className="mt-2 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  onChange={(event) =>
                    setInterviewerLinkedInUrl(event.target.value)
                  }
                  placeholder="https://www.linkedin.com/in/nombre"
                  required
                  type="url"
                  value={interviewerLinkedInUrl}
                />
              </label>

              <label className="block text-sm font-medium">
                Notas adicionales
                <textarea
                  className="mt-2 min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Contexto, foco de la entrevista, dudas o señales que querés preparar."
                  value={notes}
                />
              </label>

              {error ? (
                <p className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                  {error}
                </p>
              ) : null}

              <Button className="w-full" disabled={submitting} type="submit">
                Generar mi Kit de Entrevista
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Progreso</CardTitle>
            <CardDescription>
              La generación combina análisis del puesto, LinkedIn y tu perfil.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ProgressSteps
              companyName={companyName}
              currentStep={currentStep}
              failed={failed}
              interviewerName={interviewerName}
            />
          </CardContent>
        </Card>
      </div>

      <TaskPoller
        onComplete={handleJobAnalyzed}
        onFail={handleTaskFail}
        taskId={jobTaskId}
      />
      <TaskPoller
        onComplete={handleKitComplete}
        onFail={handleTaskFail}
        taskId={kitTaskId}
      />
    </main>
  );
}
