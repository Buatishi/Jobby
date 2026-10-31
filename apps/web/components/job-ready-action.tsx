"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n/provider";
import { waitForMatch } from "@/lib/jobs/wait-for-match";

type JobReadyActionViewProps = {
  /** Id del puesto que devolvió `POST /jobs/analyze`. */
  jobId: string;
  /** El match ya está guardado (o se agotó la espera): se puede abrir el puesto. */
  ready: boolean;
};

export function JobReadyActionView({ jobId, ready }: JobReadyActionViewProps) {
  const { t } = useI18n();

  if (!ready) {
    return (
      <Button disabled isLoading size="sm" variant="secondary">
        {t("app.matchPreparing")}
      </Button>
    );
  }

  return (
    <Button asChild size="sm">
      <Link href={`/jobs/${jobId}`}>
        {t("app.viewJob")}
        <ArrowRight className="h-4 w-4" />
      </Link>
    </Button>
  );
}

/**
 * Botón que lleva al puesto recién analizado. El análisis avisa «listo» antes de que se
 * calcule el match, y abrir el puesto en ese hueco mostraba «Match no encontrado»: el
 * botón espera a que el match exista. Si no aparece en un minuto y medio, igual se
 * ofrece el enlace: el puesto está analizado y la persona puede volver a mirarlo.
 */
export function JobReadyAction({ jobId }: { jobId: string }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void waitForMatch(() => apiClient<unknown>(`/api/v1/matches/${jobId}`), {
      signal: controller.signal
    }).then(() => {
      if (!controller.signal.aborted) {
        setReady(true);
      }
    });

    return () => controller.abort();
  }, [jobId]);

  return <JobReadyActionView jobId={jobId} ready={ready} />;
}
