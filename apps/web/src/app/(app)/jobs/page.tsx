"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { useApiResource } from "@/lib/api/use-api-resource";
import type { JobSummary } from "@/lib/jobs/job-edit";

import { JobCard } from "./job-card";

export default function JobsPage() {
  const {
    data: jobs = [],
    error,
    loading: isLoading,
    mutate
  } = useApiResource<JobSummary[]>("/api/v1/jobs", "No se pudieron cargar los jobs.");

  function handleUpdated(updated: JobSummary) {
    mutate((current) =>
      current?.map((job) => (job.id === updated.id ? { ...job, ...updated } : job))
    );
  }

  function handleDeleted(jobId: string) {
    mutate((current) => current?.filter((job) => job.id !== jobId));
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[#0F6E56]">Historial</p>
          <h1 className="text-3xl font-semibold">Jobs analizados</h1>
          <p className="mt-2 text-muted-foreground">
            Tus puestos analizados aparecen acá cuando finaliza el análisis.
          </p>
        </div>
        <Button asChild>
          <Link href="/dashboard">Analizar nuevo job</Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando jobs...
        </div>
      ) : null}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {!isLoading && !error && jobs.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Todavía no analizaste puestos</CardTitle>
            <CardDescription>
              Volvé al dashboard y pegá una URL o descripción para empezar.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      <div className="grid gap-3">
        {jobs.map((job) => (
          <JobCard
            job={job}
            key={job.id}
            onDeleted={handleDeleted}
            onUpdated={handleUpdated}
          />
        ))}
      </div>
    </main>
  );
}
