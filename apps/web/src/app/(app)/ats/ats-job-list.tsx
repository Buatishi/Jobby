"use client";

import Link from "next/link";
import { FileSearch, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { useApiResource } from "@/lib/api/use-api-resource";
import { useI18n } from "@/lib/i18n/provider";
import type { JobSummary } from "@/lib/jobs/job-edit";

export function AtsJobList() {
  const { t } = useI18n();
  // Misma ruta que la página de jobs: comparten la respuesta guardada en la pestaña.
  const {
    data: jobs = [],
    error,
    loading: isLoading
  } = useApiResource<JobSummary[]>("/api/v1/jobs", t("app.atsLoadError"));

  if (isLoading) {
    return (
      <div className="mt-5 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t("app.atsLoading")}
      </div>
    );
  }

  // Con un error y sin datos no se sabe si hay puestos: no se muestra el vacío.
  if (jobs.length === 0) {
    if (error) {
      return <p className="mt-5 text-sm text-destructive">{error}</p>;
    }

    return (
      <Card className="mt-5">
        <CardHeader>
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-[14px] bg-brand-ink text-brand-bright">
            <FileSearch className="h-5 w-5" />
          </div>
          <CardTitle>{t("app.atsEmptyTitle")}</CardTitle>
          <CardDescription>{t("app.atsEmptyDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/dashboard">{t("app.atsAnalyzeNew")}</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <section className="mt-5 space-y-3">
      <div>
        <h2 className="text-lg font-semibold">{t("app.atsListTitle")}</h2>
        <p className="text-sm text-muted-foreground">
          {t("app.atsListDescription")}
        </p>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <ul className="grid gap-3">
        {jobs.map((job) => (
          <li key={job.id}>
            <Card>
              <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium">
                    {job.job_title || t("app.untitledRole")}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {job.company_name || t("app.unnamedCompany")}
                  </p>
                </div>
                <Button asChild variant="secondary">
                  <Link href={`/ats/${job.id}`}>{t("app.viewAtsReport")}</Link>
                </Button>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </section>
  );
}
