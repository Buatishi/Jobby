"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";

import { PageBanner } from "@/components/page-banner";
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
    <main className="min-h-screen bg-white p-4 pb-14">
      <PageBanner
        actions={
          <Button asChild>
            <Link href="/dashboard">Analizar nuevo job</Link>
          </Button>
        }
        description="Tus puestos analizados aparecen acá cuando finaliza el análisis."
        eyebrow="Historial"
        title="Jobs analizados"
      />

      <div className="mt-5 space-y-5">
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
      </div>
    </main>
  );
}
