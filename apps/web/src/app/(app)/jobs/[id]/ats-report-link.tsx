"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";

type AtsReportLinkProps = {
  /** Id del puesto (`report.job_id`), no el de la ruta: `/jobs/[id]` también llega con un id de match. */
  jobId: string;
};

export function AtsReportLink({ jobId }: AtsReportLinkProps) {
  const { t } = useI18n();

  return (
    <Button asChild>
      <Link href={`/ats/${jobId}`}>{t("app.viewAtsReport")}</Link>
    </Button>
  );
}
