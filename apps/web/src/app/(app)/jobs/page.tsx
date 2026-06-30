"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";

type Job = {
  id: string;
  company_name?: string | null;
  job_title?: string | null;
  created_at?: string | null;
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient<Job[]>("/api/v1/jobs")
      .then(setJobs)
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No se pudieron cargar los jobs."
        );
      })
      .finally(() => setIsLoading(false));
  }, []);

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
          <Card key={job.id}>
            <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium">{job.job_title || "Puesto sin título"}</p>
                <p className="text-sm text-muted-foreground">
                  {job.company_name || "Empresa no detectada"}
                </p>
              </div>
              <Button asChild variant="secondary">
                <Link href={`/jobs/${job.id}`}>Ver reporte</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
